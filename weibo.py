import weibo

APP_KEY = '你的App Key'
APP_SECRET = '你的App Secret'
CALLBACK_URL = '你的回调地址'

client = weibo.APIClient(app_key=APP_KEY,
                        app_secret=APP_SECRET,
                        redirect_uri=CALLBACK_URL)

# 第一步：获取授权URL
auth_url = client.get_authorize_url()
print("请访问此URL并授权:", auth_url)

# 第二步：用户授权后，微博会跳转到回调地址，从URL参数中获取code
code = input("请输入回调URL中的code参数: ")

# 第三步：用code换取access_token
r = client.request_access_token(code)
access_token = r.access_token
expires_in = r.expires_in  # token有效期(秒)

# 保存access_token供后续使用
client.set_access_token(access_token, expires_in)