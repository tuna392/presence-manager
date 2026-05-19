import os
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker


# 1. データベースへの接続設定
# Vercelなどの環境変数から、データベースのURL（接続パスワードのようなもの）を取得する
raw_url = os.environ.get("POSTGRES_URL")

# VercelのPostgreSQL特有の仕様への対応
# URLが "postgres://" で始まっている場合、SQLAlchemyが読み込めるように "postgresql://" に変換する
DB_URL = raw_url.replace("postgres://", "postgresql://", 1) if raw_url else None

# データベースとやり取りするための「エンジン」と「セッション（接続の窓口）」を作成
eng = create_engine(DB_URL) if DB_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng) if eng else None

# テーブル設計図のベース（土台）となるクラス
Base = declarative_base()



# 2. データベースのテーブル設計図（SQLAlchemy モデル）
# ここで定義したクラスが、実際のデータベース内に「表」として作られる

class DBMember(Base):
    __tablename__ = "lab_members_v2" 
    id = Column(Integer, primary_key=True, index=True) # 通し番号（自動で1, 2, 3...と増える）
    name = Column(String)                              # メンバーの名前
    status = Column(String, default="帰宅")             # 現在のステータス（初期値は帰宅）
    is_admin = Column(Boolean, default=False)          # 管理者権限（現在は不使用だが拡張用に用意）
    updated_at = Column(DateTime, default=datetime.now)# 最後にステータスを変更した時間
    order_index = Column(Integer, default=0)           # 画面に表示する時の並び順（ドラッグ＆ドロップ用）

# システム全体の設定を保存するテーブル（常にid=1の1行だけを使う）
class DBSettings(Base):
    __tablename__ = "lab_settings_v2"
    id = Column(Integer, primary_key=True)
    show_duration = Column(Boolean, default=True)      # 学生画面に「経過時間」を表示するかどうか
    status_list = Column(String, default="在席,食事,外出,帰宅") # 選択できるステータス（カンマ区切り）

# 誰がいつステータスを変えたかの「履歴（タイムカード）」を永遠に保存するテーブル
# ※今週の滞在時間を計算するために非常に重要なテーブル
class DBStatusLog(Base):
    __tablename__ = "lab_status_logs"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, index=True)            # 誰の履歴か（DBMemberのidと紐づく）
    status = Column(String)                            # 変更後のステータス
    timestamp = Column(DateTime, default=datetime.now) # 変更した時間

# 上記で作った設計図をもとに、まだデータベースに表が存在しなければ自動で作成する
if eng:
    Base.metadata.create_all(bind=eng)



# 3. APIが受け取るデータの設計図（Pydantic モデル）
# フロントエンド（iPad等）から送られてくるデータの「型」や「必須項目」をチェックする

# 新しくメンバーを追加する時に送られてくるデータ
class MemberCreate(BaseModel):
    name: str
    is_admin: bool = False

# メンバーのステータスを変更する時に送られてくるデータ
class StatusUpdate(BaseModel):
    id: int
    status: str

# 管理画面でシステム設定を保存する時に送られてくるデータ
class SettingUpdate(BaseModel):
    show_duration: bool
    status_list: str

# ドラッグ＆ドロップで順番を入れ替えた時に送られてくるデータ
class MemberReorder(BaseModel):
    ordered_ids: list[int] # 新しい順番に並んだIDのリスト



# 4. データベース接続を提供する関数（Dependency Injection）
def get_db():
    if SessionLocal is None: return
    db = SessionLocal() # データベースへの接続を開く
    try:
        yield db        # APIの処理中にデータベースを使わせる
    finally:
        db.close()      # APIの処理が終わったら、確実に接続を閉じる（メモリの無駄遣いを防ぐ）