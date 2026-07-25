from google import genai
from PIL import Image
import streamlit as st

# 画面のタイトル
st.title("手書きメモ文字起こしアプリ")

# APIキーの入力欄
api_key = st.text_input("Google AI StudioのAPIキーを入力してください", type="password")

# 画像をアップロードするボタン
uploaded_file = st.file_uploader(
    "手書きメモの画像をアップロードしてください", type=["jpg", "png", "jpeg"]
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

          # ★ 最新の標準モデル「gemini-2.0-flash」に修正しました！
          response = client.models.generate_content(
              model="gemini-2.0-flash",
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
