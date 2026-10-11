import json
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from PIL import Image

# レシートを保存するSQLiteファイル（このアプリを動かしているパソコン上に作られる）
DB_PATH = Path(__file__).with_name("okaimono.db")


def db_connect():
  con = sqlite3.connect(DB_PATH)
  con.execute("PRAGMA foreign_keys = ON")
  con.executescript(
      """
      CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchased_on TEXT NOT NULL,
        total INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      );
      CREATE TABLE IF NOT EXISTS receipt_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        price INTEGER NOT NULL
      );
      """
  )
  return con


def save_receipt(purchased_on, items):
  total = sum(i["price"] for i in items)
  with db_connect() as con:
    cur = con.execute(
        "INSERT INTO receipts (purchased_on, total) VALUES (?, ?)",
        (purchased_on, total),
    )
    con.executemany(
        "INSERT INTO receipt_items (receipt_id, name, price) VALUES (?, ?, ?)",
        [(cur.lastrowid, i["name"], i["price"]) for i in items],
    )
  return total


def monthly_totals():
  with db_connect() as con:
    return pd.read_sql_query(
        "SELECT substr(purchased_on, 1, 7) AS 月, SUM(total) AS 支出合計, COUNT(*) AS 件数 "
        "FROM receipts GROUP BY 月 ORDER BY 月",
        con,
    )


def list_receipts():
  with db_connect() as con:
    return pd.read_sql_query(
        "SELECT r.id AS ID, r.purchased_on AS 日付, r.total AS 合計, COUNT(i.id) AS 品数 "
        "FROM receipts r LEFT JOIN receipt_items i ON i.receipt_id = r.id "
        "GROUP BY r.id ORDER BY r.purchased_on DESC, r.id DESC",
        con,
    )


def delete_receipt(receipt_id):
  with db_connect() as con:
    con.execute("DELETE FROM receipts WHERE id = ?", (receipt_id,))


def read_receipt(client, model, image):
  response = client.models.generate_content(
      model=model,
      contents=[
          image,
          (
              "この画像はレシートです。購入された商品名と税込の価格をすべて読み取り、"
              'JSONだけで {"items": [{"name": "商品名", "price": 123}]} の形式で返してください。'
              "価格が読めない商品は含めないでください。"
          ),
      ],
      config=types.GenerateContentConfig(response_mime_type="application/json"),
  )
  data = json.loads(response.text)
  items = []
  for it in data.get("items", []):
    try:
      name, price = str(it["name"]).strip(), int(it["price"])
    except (KeyError, TypeError, ValueError):
      continue
    if name:
      items.append({"name": name, "price": price})
  return items


# 画面のタイトル
st.title("おかいものメモ（Gemini読み取り）")

# APIキー・モデルの入力欄
api_key = st.text_input("Google AI StudioのAPIキーを入力してください", type="password")
model = st.text_input("モデル名", value="gemini-3.5-flash-lite")

tab_memo, tab_receipt, tab_spend = st.tabs(["手書きメモ", "レシート保存", "支出推移"])

with tab_memo:
  # 画像をアップロードするボタン
  uploaded_file = st.file_uploader(
      "手書きメモの画像をアップロードしてください", type=["jpg", "png", "jpeg"], key="memo"
  )

  if uploaded_file is not None:
    # アップロードされた画像をPillowの画像形式に変換して表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされたメモ", use_column_width=True)

    if st.button("文字起こしを実行する"):
      if not api_key:
        st.error("APIキーを入力してください。")
      else:
        with st.spinner("AIが文字を読み取り中..."):
          try:
            # Geminiクライアントの初期化
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=[
                    image,
                    (
                        "この画像に書かれている手書きの文字を正確に読み取り、"
                        "テキストとして書き起こしてください。"
                    ),
                ],
            )

            st.success("読み取り完了！")
            st.write("### 読み取り結果:")
            st.write(response.text)

          except Exception as e:
            st.error(f"エラーが発生しました: {e}")

with tab_receipt:
  receipt_file = st.file_uploader(
      "レシートの画像をアップロードしてください", type=["jpg", "png", "jpeg"], key="receipt"
  )
  if receipt_file is not None:
    receipt_image = Image.open(receipt_file)
    st.image(receipt_image, caption="アップロードされたレシート", use_column_width=True)

    if st.button("読み取る"):
      if not api_key:
        st.error("APIキーを入力してください。")
      else:
        with st.spinner("レシートを読み取り中..."):
          try:
            items = read_receipt(genai.Client(api_key=api_key), model, receipt_image)
            if items:
              st.session_state["receipt_items"] = items
            else:
              st.session_state.pop("receipt_items", None)
              st.error("品目を読み取れませんでした。撮り直してみてください。")
          except Exception as e:
            st.error(f"エラーが発生しました: {e}")

    if "receipt_items" in st.session_state:
      st.write("### 読み取り結果（修正できます）")
      edited = st.data_editor(
          pd.DataFrame(st.session_state["receipt_items"]),
          num_rows="dynamic",
          use_container_width=True,
      )
      purchased_on = st.date_input("購入日", value=date.today())
      if st.button("DBに保存する"):
        rows = [
            {"name": str(r["name"]).strip(), "price": int(r["price"])}
            for _, r in edited.dropna().iterrows()
            if str(r["name"]).strip()
        ]
        if rows:
          total = save_receipt(purchased_on.isoformat(), rows)
          st.session_state.pop("receipt_items", None)
          st.success(f"{DB_PATH.name} に保存しました（合計 {total:,} 円）")
        else:
          st.error("保存する品目がありません。")

with tab_spend:
  monthly = monthly_totals()
  if monthly.empty:
    st.info("まだレシートが保存されていません。")
  else:
    st.write("### 月別の支出推移")
    st.bar_chart(monthly.set_index("月")["支出合計"])
    st.dataframe(monthly, use_container_width=True, hide_index=True)
    st.write("### 保存済みレシート")
    st.dataframe(list_receipts(), use_container_width=True, hide_index=True)
    del_id = st.number_input("削除するレシートID", min_value=1, step=1)
    if st.button("削除する"):
      delete_receipt(int(del_id))
      st.rerun()
