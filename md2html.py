#!/usr/bin/env python3
"""
md2html.py - 将 Markdown 文件批量转换为美观的 HTML 页面

功能：
1. 扫描 docs/ 下所有 .md 文件
2. 转换为 GitHub 暗色主题的 HTML
3. 自动生成目录索引页
4. 支持表格、代码高亮、链接等 Markdown 特性

用法：
  python3 md2html.py                          # 转换所有 .md
  python3 md2html.py daily                     # 只转换 daily/ 目录
  python3 md2html.py /path/to/specific.md      # 转换单个文件
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

# 尝试导入 markdown 库
MARKDOWN_AVAILABLE = False
try:
    import markdown as md_lib
    MARKDOWN_AVAILABLE = True
except ImportError:
    print("⚠️ 未安装 python-markdown，将使用内置简单转换器")
    print("   安装：pip install markdown 或 uv pip install markdown")


# ============================================================
# HTML 模板（GitHub 暗色主题风格）
# ============================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Hermes 交易系统</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
      background: #0d1117;
      color: #c9d1d9;
      line-height: 1.7;
      max-width: 920px;
      margin: 0 auto;
      padding: 40px 24px;
    }}
    h1, h2, h3 {{ margin-top: 32px; margin-bottom: 16px; font-weight: 600; line-height: 1.25; }}
    h1 {{ font-size: 32px; color: #58a6ff; border-bottom: 1px solid #21262d; padding-bottom: 10px; letter-spacing: -0.5px; }}
    h2 {{ font-size: 24px; color: #f0c674; }}
    h3 {{ font-size: 20px; color: #d2a8f3; }}
    h4 {{ font-size: 16px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; margin-top: 24px; }}
    p {{ margin: 12px 0; }}
    a {{ color: #58a6ff; text-decoration: none; }}
    a:hover {{ text-decoration: underline; color: #79c0ff; }}
    strong {{ color: #f0f6fc; }}
    em {{ color: #8b949e; }}
    table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin: 20px 0;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      border-bottom: 1px solid #21262d;
    }}
    th {{
      background: #1c2128;
      color: #8b949e;
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #1c2333; }}
    code {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 4px;
      padding: 2px 6px;
      font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
      font-size: 14px;
      color: #ffa657;
    }}
    pre {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 16px;
      overflow-x: auto;
      margin: 16px 0;
    }}
    pre code {{
      background: none;
      border: none;
      padding: 0;
      color: #79c0ff;
      font-size: 13px;
      line-height: 1.5;
    }}
    blockquote {{
      border-left: 4px solid #30363d;
      padding: 8px 16px;
      margin: 16px 0;
      background: #161b22;
      border-radius: 0 6px 6px 0;
      color: #8b949e;
    }}
    ul, ol {{ margin: 12px 0; padding-left: 24px; }}
    li {{ margin: 6px 0; }}
    hr {{
      border: none;
      border-top: 1px solid #21262d;
      margin: 32px 0;
    }}
    img {{ max-width: 100%; border-radius: 8px; margin: 16px 0; }}
    .header-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0;
      margin-bottom: 24px;
      border-bottom: 1px solid #21262d;
    }}
    .nav-links {{
      display: flex;
      gap: 12px;
    }}
    .nav-links a {{
      padding: 6px 14px;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #8b949e;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.2s;
    }}
    .nav-links a:hover {{
      background: #1c2333;
      border-color: #58a6ff;
      color: #58a6ff;
      text-decoration: none;
    }}
    .footer {{
      margin-top: 48px;
      padding-top: 16px;
      border-top: 1px solid #21262d;
      text-align: center;
      color: #484f58;
      font-size: 12px;
    }}
    .footer a {{ color: #484f58; }}
    .footer a:hover {{ color: #8b949e; }}
    .tag {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 600;
    }}
    .tag-profit {{ background: rgba(63, 185, 80, 0.15); color: #3fb950; }}
    .tag-loss {{ background: rgba(248, 81, 73, 0.15); color: #f85149; }}
    .tag-info {{ background: rgba(88, 166, 255, 0.15); color: #58a6ff; }}
    .tag-warn {{ background: rgba(240, 198, 116, 0.15); color: #f0c674; }}
    @media (max-width: 640px) {{
      body {{ padding: 20px 12px; }}
      h1 {{ font-size: 24px; }}
      .header-bar {{ flex-direction: column; gap: 12px; }}
    }}
  </style>
</head>
<body>
  <div class="header-bar">
    <div style="font-weight:600; color:#58a6ff; font-size:14px;">⚡ Hermes 自进化交易系统</div>
    <div class="nav-links">
      <a href="/hermes_stock/">🏠 首页</a>
      <a href="/hermes_stock/daily/">📅 每日报告</a>
      <a href="/hermes_stock/backtest/">📊 回测</a>
      <a href="/hermes_stock/strategy/">🧬 策略</a>
    </div>
  </div>
  
  {content}
  
  <div class="footer">
    由 Hermes 自进化交易系统自动生成 · <a href="https://github.com/kirasq/hermes_stock">GitHub 仓库</a><br>
    更新时间：{update_time} · ⚠️ 所有交易均为模拟盘
  </div>
</body>
</html>"""


# ============================================================
# 简单 Markdown → HTML 转换（无依赖 fallback）
# ============================================================
def simple_md_to_html(md_text):
    """不依赖外部库的 Markdown 简单转换器"""
    lines = md_text.split('\n')
    html = []
    in_list = False
    list_type = None
    in_table = False
    in_code = False
    code_buffer = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 代码块（```）
        if line.strip().startswith('```'):
            if in_code:
                html.append(f'<pre><code>{"".join(code_buffer).rstrip()}</code></pre>')
                code_buffer = []
                in_code = False
            else:
                in_code = True
                code_buffer = []
            i += 1
            continue
        
        if in_code:
            code_buffer.append(line + '\n')
            i += 1
            continue
        
        # 空行
        if not line.strip():
            if in_list:
                html.append(f'</{"ol" if list_type == "ordered" else "ul"}>\n')
                in_list = False
                list_type = None
            html.append('<br>\n')
            i += 1
            continue
        
        # 水平线
        if re.match(r'^---+$', line.strip()):
            html.append('<hr>\n')
            i += 1
            continue
        
        # 标题
        h_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if h_match:
            level = len(h_match.group(1))
            text = h_match.group(2)
            html.append(f'<h{level}>{text}</h{level}>\n')
            i += 1
            continue
        
        # 表格
        if '|' in line and re.match(r'^\s*\|', line):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if not in_table:
                html.append('<table>\n')
                in_table = True
                # 判断是不是表头行下面那行（分隔线）
                next_line = lines[i+1] if i+1 < len(lines) else ''
                if re.match(r'^\s*\|[\s:-]+\|', next_line):
                    html.append('  <thead><tr>\n')
                    for c in cells:
                        html.append(f'    <th>{c}</th>\n')
                    html.append('  </tr></thead>\n')
                    html.append('  <tbody>\n')
                    i += 2  # skip separator line
                    continue
            html.append('  <tr>\n')
            for c in cells:
                html.append(f'    <td>{c}</td>\n')
            html.append('  </tr>\n')
            i += 1
            continue
        else:
            if in_table:
                html.append('  </tbody>\n</table>\n')
                in_table = False
        
        # 列表
        ul_match = re.match(r'^[-*+]\s+(.+)$', line)
        ol_match = re.match(r'^\d+[.)]\s+(.+)$', line)
        
        if ul_match:
            if not in_list or list_type == "ordered":
                if in_list:
                    html.append(f'</{"ol" if list_type == "ordered" else "ul"}>\n')
                html.append('<ul>\n')
                in_list = True
                list_type = "unordered"
            html.append(f'  <li>{ul_match.group(1)}</li>\n')
            i += 1
            continue
        elif ol_match:
            if not in_list or list_type == "unordered":
                if in_list:
                    html.append(f'</{"ol" if list_type == "ordered" else "ul"}>\n')
                html.append('<ol>\n')
                in_list = True
                list_type = "ordered"
            html.append(f'  <li>{ol_match.group(1)}</li>\n')
            i += 1
            continue
        else:
            if in_list:
                html.append(f'</{"ol" if list_type == "ordered" else "ul"}>\n')
                in_list = False
                list_type = None
        
        # 普通段落（内联格式处理）
        text = line.strip()
        if text:
            # 内联格式
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
            text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
            html.append(f'<p>{text}</p>\n')
        
        i += 1
    
    # 关闭未闭合的标签
    if in_list:
        html.append(f'</{"ol" if list_type == "ordered" else "ul"}>\n')
    if in_table:
        html.append('  </tbody>\n</table>\n')
    if in_code:
        html.append(f'<pre><code>{"".join(code_buffer).rstrip()}</code></pre>\n')
    
    return ''.join(html)


# ============================================================
# 主转换函数
# ============================================================
def md_to_html(md_text):
    """将 Markdown 转为 HTML 内容（使用 markdown 库或 fallback）"""
    if MARKDOWN_AVAILABLE:
        # 使用专业 markdown 库
        extensions = [
            'tables',
            'fenced_code',
            'codehilite',
            'nl2br',
            'sane_lists',
            'smarty',
        ]
        return md_lib.markdown(md_text, extensions=extensions)
    else:
        # 使用内置简单转换器
        return simple_md_to_html(md_text)


def extract_title(md_text):
    """从 Markdown 中提取标题"""
    match = re.search(r'^#\s+(.+)$', md_text, re.MULTILINE)
    return match.group(1).strip() if match else "报告"


def infer_directory(filepath):
    """从文件路径推断所属目录名称"""
    path = Path(filepath)
    parent = path.parent.name
    if parent == 'docs':
        return 'root'
    return parent


def convert_file(md_path, output_dir=None):
    """转换单个 Markdown 文件到 HTML"""
    md_path = Path(md_path)
    if not md_path.exists():
        print(f"❌ 文件不存在：{md_path}")
        return False
    
    md_content = md_path.read_text(encoding="utf-8")
    title = extract_title(md_content)
    html_body = md_to_html(md_content)
    
    # 构建输出路径
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = md_path.parent
    
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{md_path.stem}.html"
    
    # 填充模板
    full_html = HTML_TEMPLATE.format(
        title=title,
        content=html_body,
        update_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    html_path.write_text(full_html, encoding="utf-8")
    print(f"✅ {md_path.name} → {html_path.name}")
    return True


def scan_and_convert(directory):
    """扫描目录下所有 .md 文件并转换"""
    base = Path("/opt/data/hermes_stock/docs")
    target = base / directory if directory else base
    
    if not target.exists():
        print(f"❌ 目录不存在：{target}")
        return 0
    
    md_files = list(target.glob("*.md"))
    # 排除 index.md（它只是目录索引，不是报告）
    md_files = [f for f in md_files if f.name != 'index.md']
    
    if not md_files:
        print(f"ℹ️  {target} 下没有 .md 文件需要转换")
        return 0
    
    success = 0
    for md_file in sorted(md_files):
        try:
            if convert_file(md_file, output_dir=target):
                success += 1
        except Exception as e:
            print(f"❌ {md_file.name} 转换失败：{e}")
    
    return success


def generate_main_index():
    """生成 docs/ 主索引页"""
    docs_dir = Path("/opt/data/hermes_stock/docs")
    index_path = docs_dir / "index.html"
    
    categories = {
        "daily": ("📅 每日交易报告", "每日汇总、复盘、晨间资讯"),
        "backtest": ("📊 策略回测", "策略指标、参数配置、收益分析"),
        "strategy": ("🧬 策略进化日志", "自进化历史、参数变更记录"),
        "wikillm": ("📚 WikiLLM 知识库", "股票知识文档集"),
    }
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hermes 自进化交易系统</title>
  <link rel="stylesheet" href="https://kirasq.github.io/hermes_stock/docs/daily/index.html">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans SC', sans-serif;
      background: #0d1117;
      color: #c9d1d9;
      max-width: 800px;
      margin: 0 auto;
      padding: 60px 24px;
    }}
    h1 {{ color: #58a6ff; font-size: 36px; margin-bottom: 8px; }}
    .subtitle {{ color: #8b949e; font-size: 16px; margin-bottom: 40px; }}
    .card {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 20px;
      margin: 16px 0;
      transition: border-color 0.2s;
    }}
    .card:hover {{ border-color: #58a6ff; }}
    .card h2 {{ color: #f0c674; font-size: 20px; margin-bottom: 6px; }}
    .card p {{ color: #8b949e; font-size: 14px; }}
    .card a {{ text-decoration: none; display: block; }}
    .status-section {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 24px;
      margin: 32px 0;
    }}
    .status-section h3 {{ color: #58a6ff; margin-bottom: 16px; }}
    .service-list {{ list-style: none; padding: 0; }}
    .service-list li {{
      padding: 8px 0;
      border-bottom: 1px solid #21262d;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .service-list li:last-child {{ border-bottom: none; }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
    .dot-ok {{ background: #3fb950; }}
    .dot-off {{ background: #484f58; }}
    .tag {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 600;
      background: rgba(63, 185, 80, 0.15);
      color: #3fb950;
    }}
  </style>
</head>
<body>
  <h1>⚡ Hermes 自进化交易系统</h1>
  <p class="subtitle">最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  
  <div class="status-section">
    <h3>📡 系统状态</h3>
    <ul class="service-list">
      <li><span class="dot dot-ok"></span> 飞书网关 — 已连接</li>
      <li><span class="dot dot-ok"></span> 晨间资讯 (08:30) — <span class="tag">活跃</span></li>
      <li><span class="dot dot-ok"></span> 盘中监控 (每30分钟) — <span class="tag">活跃</span></li>
      <li><span class="dot dot-ok"></span> 盘后复盘 (19:00) — <span class="tag">活跃</span></li>
      <li><span class="dot dot-ok"></span> 策略自进化 (20:00) — <span class="tag">活跃</span></li>
      <li><span class="dot dot-ok"></span> GitHub Pages — <span class="tag">已部署</span></li>
    </ul>
  </div>
  
  <h3 style="color:#f0c674; margin: 24px 0 16px;">📂 报告导航</h3>"""
    
    for key, (title, desc) in categories.items():
        html += f"""
  <a href="{key}/" style="text-decoration:none;">
    <div class="card">
      <h2>{title}</h2>
      <p>{desc}</p>
    </div>
  </a>"""
    
    html += """
  <hr style="border-color:#21262d; margin:40px 0;">
  <p style="text-align:center; color:#484f58; font-size:12px;">
    ⚠️ 所有交易均为模拟盘 · 由 Hermes 系统自动管理 · 
    <a href="https://github.com/kirasq/hermes_stock" style="color:#484f58;">GitHub 仓库</a>
  </p>
</body>
</html>"""
    
    index_path.write_text(html, encoding="utf-8")
    print(f"✅ 主索引页已更新：{index_path}")
    return True


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    print(f"{'='*50}")
    print(f"  Markdown → HTML 转换器")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    args = sys.argv[1:] if len(sys.argv) > 1 else ["all"]
    
    for arg in args:
        if arg == "all" or arg == "全部":
            # 转换所有目录
            total = 0
            for dir_name in ["daily", "backtest", "strategy", "wikillm", "reviews"]:
                total += scan_and_convert(dir_name)
            generate_main_index()
            print(f"\n📊 共转换 {total} 个文件")
            
        elif arg == "daily":
            count = scan_and_convert("daily")
            generate_main_index()
            print(f"\n📊 转换 {count} 个每日报告")
            
        elif arg == "backtest":
            count = scan_and_convert("backtest")
            print(f"\n📊 转换 {count} 个回测报告")
            
        elif arg == "strategy":
            count = scan_and_convert("strategy")
            print(f"\n📊 转换 {count} 个策略报告")
            
        elif arg == "wikillm":
            count = scan_and_convert("wikillm")
            print(f"\n📊 转换 {count} 个知识库文档")
            
        elif Path(arg).exists() and arg.endswith('.md'):
            convert_file(arg)
            
        else:
            print(f"❌ 未知参数：{arg}")
            print("用法：python3 md2html.py [daily|backtest|strategy|wikillm|all]")
