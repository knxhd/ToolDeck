import requests

url = "http://10.18.217.60:32013/api/file/uploadFile"

files = [
    ("file", ("2026-10-22_工具后台_需求说明_v5_codex327.html", open("D:\\download\\2026-10-22_工具后台_需求说明_v5_codex327.html", "rb")))
]

response = requests.request("POST", url, files=files)

print(response.status_code)
print(response.text)