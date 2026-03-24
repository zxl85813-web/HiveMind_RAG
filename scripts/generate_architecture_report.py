import os
import requests
import json
import sys

def generate_report():
    # 捕获各阶段状态（从环境变量传入）
    results = {
        "Phase 1: Capacity": os.getenv("PHASE1_RESULT", "unknown"),
        "Phase 2: Chaos": os.getenv("PHASE2_RESULT", "unknown"),
        "Phase 3: Endurance": os.getenv("PHASE3_RESULT", "unknown"),
        "Phase 4: Telemetry": os.getenv("PHASE4_RESULT", "unknown"),
    }
    
    # 构造专业架构 Prompt
    prompt = (
        f"作为系统架构师，请针对以下 HiveMind RAG 项目的 CI 架构评测结果生成一份 Markdown 总结报告：\n"
        f"{json.dumps(results, indent=2)}\n\n"
        f"要求：\n"
        f"1. 针对每个 Phase 给出简短的架构点评（成功则说明增益，失败则指出风险）。\n"
        f"2. 给出 1-2 条明确的架构演进建议。\n"
        f"3. 报告末尾署名 'HiveMind 自动化架构师 (Antigravity)'。\n"
        f"请直接输出报告正文，不要包含任何前导说明。"
    )

    # 🛰️ [Architecture-Gate]: 直接调用云端模型提供商，不依赖可能不稳定的本地 Backend
    llm_api_key = os.getenv("LLM_API_KEY", "")
    # 使用标准 API 端点，避免使用 CI 内不确定的 VITE_API_BASE_URL
    api_url = "https://api.siliconflow.cn/v1/chat/completions"
    
    if not llm_api_key:
        print("Skipping LLM analysis: LLM_API_KEY not found.")
        # Write a placeholder report if API key is missing
        with open("architecture_report.md", "w", encoding="utf-8") as f:
            f.write("# 🏛️ HiveMind 架构评测自动汇总\n\n")
            f.write("## ⚠️ 架构评测概览 (LLM_API_KEY 缺失)\n\n")
            f.write("LLM_API_KEY 环境变量未设置，无法生成详细报告。请检查您的 GitHub Secrets。\n\n")
            f.write(f"原始结果: {json.dumps(results, indent=2)}")
        return

    # 获取环境变量中的模型配置，默认使用 DeepSeek
    model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3")

    print(f"Generating report using model: {model}")

    try:
        # 使用项目已有的 SiliconFlow 接口
        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {llm_api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=45
        )
        
        if response.status_code == 200:
            report_content = response.json()['choices'][0]['message']['content']
        else:
            report_content = f"## ⚠️ 架构评测概览 (LLM 接口返回异常: {response.status_code})\n\n结果详情: {json.dumps(results)}"
            
    except Exception as e:
        report_content = f"## 🛠 架构评测概览 (报告生成脚本异常)\n\n异常信息: {str(e)}\n\n原始结果: {json.dumps(results)}"

    # 写入 GitHub Step Summary 所需的格式
    with open("architecture_report.md", "w", encoding="utf-8") as f:
        f.write("# 🏛️ HiveMind 架构评测自动汇总\n\n")
        f.write(report_content)

if __name__ == "__main__":
    generate_report()
