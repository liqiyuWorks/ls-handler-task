from clickhouse_driver import Client
import os

# export CK_HOST=123.249.97.59
# export CK_PORT=21662
# export CK_USER=default
# export CK_PASSWORD=shipping_history123
# export CK_DB=shipping_history


class ClickHouseClient:
    def __init__(self):
        # 数据库源连接
        self.ck_host = os.getenv('CK_HOST')
        self.ck_port = os.getenv('CK_PORT')
        self.ck_user = os.getenv('CK_USER')
        self.ck_password = os.getenv('CK_PASSWORD')
        self.ck_db = os.getenv('CK_DB')
        self.client = None
        self.connect()

    def connect(self):
        """建立数据库连接"""
        try:
            self.client = Client(
                host=self.ck_host,
                port=self.ck_port,
                user=self.ck_user,
                database=self.ck_db,
                password=self.ck_password,
                send_receive_timeout=5
            )
            print("> ClickHouse client connected successfully")
        except Exception as e:
            print(f"Error connecting to ClickHouse: {e}")
            raise

    def query(self, sql):
        """执行 SQL 查询

        Args:
            sql (str): SQL 查询语句

        Returns:
            list: 查询结果
        """
        try:
            return self.client.execute(sql)
        except Exception as e:
            print(f"Error executing query: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.disconnect()
            # print("> ClickHouse client disconnected")
