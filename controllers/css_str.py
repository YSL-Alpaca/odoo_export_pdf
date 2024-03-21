# 添加样式和美化HTML
styled_html = """
    <html>
    <head>
      <meta charset="utf-8">
    </head>
    <body>
    {html_table}
    </body>
    <style>
    table {{
      font-family: arial, sans-serif;
      border-collapse: collapse;
      width: 100%;
    }}
    
    td, th {{
      border: 1px solid #dddddd;
      text-align: left;
      padding: 8px;
    }}
    
    th {{
      background-color: #dddddd;
    }}
    </style>
    </html>
"""
