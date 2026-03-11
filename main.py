# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from zhipuai import ZhipuAI
from prompts import SYSTEM_PROMPT, get_prompt

load_dotenv()

API_KEY = os.getenv("ZHIPU_API_KEY")
if not API_KEY:
    raise ValueError("没找到 ZHIPU_API_KEY，请检查 .env 文件")

client = ZhipuAI(api_key=API_KEY)
app = FastAPI()

# 定义前端发过来的数据结构
class GenRequest(BaseModel):
    doc_type: str
    material: str
    org_name: str
    date: str
    extra: str = ""

HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>公文助手 GongWen AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f2f5;
            min-height: 100vh;
            padding: 30px 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: #1a3a5c;
            font-size: 26px;
            margin-bottom: 6px;
        }

        .subtitle {
            text-align: center;
            color: #888;
            font-size: 14px;
            margin-bottom: 30px;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .card h2 {
            font-size: 16px;
            color: #1a3a5c;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e8f0fe;
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        label {
            font-size: 13px;
            color: #555;
            font-weight: 500;
        }

        select, input, textarea {
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            outline: none;
            transition: border-color 0.2s;
        }

        select:focus, input:focus, textarea:focus {
            border-color: #1a3a5c;
        }

        textarea {
            resize: vertical;
            min-height: 120px;
            line-height: 1.6;
        }

        .btn-generate {
            width: 100%;
            padding: 14px;
            background: #1a3a5c;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .btn-generate:hover { background: #24527a; }
        .btn-generate:disabled { background: #aaa; cursor: not-allowed; }

        .result-box {
            white-space: pre-wrap;
            font-family: 'SimSun', 'STSong', serif;
            font-size: 15px;
            line-height: 2;
            color: #222;
            min-height: 200px;
            padding: 10px 0;
        }

        .placeholder {
            color: #bbb;
            text-align: center;
            padding: 60px 0;
            font-size: 14px;
        }

        .btn-copy {
            float: right;
            padding: 6px 16px;
            background: #e8f0fe;
            color: #1a3a5c;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            margin-bottom: 10px;
        }

        .btn-copy:hover { background: #d0e1fc; }

        .loading {
            text-align: center;
            color: #1a3a5c;
            padding: 60px 0;
            font-size: 14px;
            display: none;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>📄 公文助手 GongWen AI</h1>
    <p class="subtitle">输入素材，一键生成标准格式党政公文</p>

    <div class="card">
        <h2>填写信息</h2>

        <div class="form-row">
            <div class="form-group">
                <label>公文类型</label>
                <select id="docType">
                    <option value="通知">通知</option>
                    <option value="情况汇报">情况汇报</option>
                    <option value="简报">简报</option>
                    <option value="会议纪要">会议纪要</option>
                </select>
            </div>
            <div class="form-group">
                <label>发文机关</label>
                <input type="text" id="orgName" placeholder="例：厦门市某某局" />
            </div>
        </div>

        <div class="form-row">
            <div class="form-group">
                <label>成文日期</label>
                <input type="date" id="date" />
            </div>
            <div class="form-group">
                <label>主送机关 / 附加要求（选填）</label>
                <input type="text" id="extra" placeholder="例：各处室、各直属单位" />
            </div>
        </div>

        <div class="form-group" style="margin-bottom:16px">
            <label>原始素材（把要写的事情说清楚就行）</label>
            <textarea id="material" placeholder="例：3月10日，我单位召开安全生产专题会议，传达上级文件精神，部署下一阶段重点工作，要求各部门于3月底前完成自查并上报结果……"></textarea>
        </div>

        <button class="btn-generate" onclick="generate()">生成公文</button>
    </div>

    <div class="card">
        <h2>生成结果
            <button class="btn-copy" onclick="copyResult()">复制全文</button>
        </h2>
        <div class="loading" id="loading">⏳ 正在生成，请稍候...</div>
        <div class="result-box" id="result">
            <div class="placeholder">生成的公文将显示在这里</div>
        </div>
    </div>
</div>

<script>
    // 默认填入今天日期
    document.getElementById('date').value = new Date().toISOString().split('T')[0];

    async function generate() {
        const material = document.getElementById('material').value.trim();
        const orgName = document.getElementById('orgName').value.trim();

        if (!material) { alert('请输入原始素材'); return; }
        if (!orgName) { alert('请填写发文机关'); return; }

        const btn = document.querySelector('.btn-generate');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');

        btn.disabled = true;
        loading.style.display = 'block';
        result.innerHTML = '';

        const dateVal = document.getElementById('date').value;
        const formattedDate = dateVal
            ? dateVal.replace(/-/g, '年').replace(/(\d{4}年)(\d{2})/, '$1$2月').replace(/(\d{2})$/, '$1日')
            : '';

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    doc_type: document.getElementById('docType').value,
                    material: material,
                    org_name: orgName,
                    date: formattedDate,
                    extra: document.getElementById('extra').value.trim()
                })
            });

            const data = await response.json();

            if (data.result) {
                result.textContent = data.result;
            } else {
                result.textContent = '出错了：' + (data.error || '未知错误');
            }

        } catch(e) {
            result.textContent = '网络错误：' + e.message;
        } finally {
            btn.disabled = false;
            loading.style.display = 'none';
        }
    }

    function copyResult() {
        const text = document.getElementById('result').textContent;
        if (!text || text.includes('生成的公文将显示在这里')) {
            alert('还没有生成内容');
            return;
        }
        navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板'));
    }
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PAGE

@app.post("/api/generate")
async def generate(req: GenRequest):
    try:
        user_prompt = get_prompt(
            req.doc_type,
            req.material,
            req.org_name,
            req.date,
            req.extra
        )

        response = client.chat.completions.create(
            model="glm-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        result = response.choices[0].message.content
        return {"result": result}

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("启动成功！访问：http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
