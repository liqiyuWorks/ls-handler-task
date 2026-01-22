import pandas as pd
import xlsxwriter

# 1. 准备数据
data = {
    '代码': ['SCHD', 'PAVE', 'COPX'],
    '名称/策略': ['防守-收息', '稳健-基建', '进攻-铜矿'],
    '持股数': [172, 58, 24],
    '平均成本': [29.15, 51.65, 83.97],
    '当前价格': [29.15, 51.65, 83.97], # 初始价格设为成本价
    '目标仓位': [0.50, 0.30, 0.20]
}

df = pd.DataFrame(data)

# 创建 Excel writer 对象
file_name = '美股持仓管理_2026.xlsx'
writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
workbook = writer.book
worksheet = workbook.add_worksheet('持仓看板')

# 定义格式
fmt_currency = workbook.add_format({'num_format': '$#,##0.00'})
fmt_percent = workbook.add_format({'num_format': '0.00%'})
fmt_header = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
fmt_bold = workbook.add_format({'bold': True})

# ----------------------------------------
# 第一部分：顶部仪表盘 (Dashboard)
# ----------------------------------------
worksheet.write('A1', '当前总资产 (Total Equity)', fmt_bold)
worksheet.write('A2', '总投入本金 (Total Cost)', fmt_bold)
worksheet.write('A3', '总浮动盈亏 (Total P&L)', fmt_bold)
worksheet.write('A4', '总收益率 (Return %)', fmt_bold)
worksheet.write('A5', '剩余现金 (Cash)', fmt_bold)

# 写入仪表盘公式
worksheet.write_formula('B1', '=F12+B5', fmt_currency) # 当前总资产 = 总市值 + 现金
worksheet.write('B2', 10000.00, fmt_currency)          # 总投入 (初始 1w)
worksheet.write_formula('B3', '=B1-B2', fmt_currency)  # 盈亏
worksheet.write_formula('B4', '=B3/B2', fmt_percent)   # 收益率
worksheet.write('B5', 0.00, fmt_currency)              # 剩余现金

# ----------------------------------------
# 第二部分：持仓明细 (Holdings)
# ----------------------------------------
# 写入表头 (从第 7 行开始, 即 Excel row 8)
headers = ['代码', '名称/策略', '持股数', '平均成本', '当前价格', '持仓市值', '盈亏金额', '盈亏比例', '当前仓位%', '目标仓位%']
for col_num, header in enumerate(headers):
    worksheet.write(6, col_num, header, fmt_header)

# 写入数据和行级公式
start_row = 7
for i, row in df.iterrows():
    curr_row = start_row + i
    row_num = curr_row + 1 # Excel 是从 1 开始计数的
    
    # 写入基础数据
    worksheet.write(curr_row, 0, row['代码'])
    worksheet.write(curr_row, 1, row['名称/策略'])
    worksheet.write(curr_row, 2, row['持股数'])
    worksheet.write(curr_row, 3, row['平均成本'], fmt_currency)
    worksheet.write(curr_row, 4, row['当前价格'], fmt_currency)
    
    # 写入计算公式
    # F列: 持仓市值 = 持股数 * 当前价格
    worksheet.write_formula(curr_row, 5, f'=C{row_num}*E{row_num}', fmt_currency)
    
    # G列: 盈亏金额 = 市值 - (持股数 * 成本)
    worksheet.write_formula(curr_row, 6, f'=F{row_num}-(C{row_num}*D{row_num})', fmt_currency)
    
    # H列: 盈亏比例 = 盈亏金额 / (持股数 * 成本)
    worksheet.write_formula(curr_row, 7, f'=G{row_num}/(C{row_num}*D{row_num})', fmt_percent)
    
    # I列: 当前仓位% = 个股市值 / 总市值 (F12)
    worksheet.write_formula(curr_row, 8, f'=F{row_num}/$F$12', fmt_percent)
    
    # J列: 目标仓位 (直接写入数据)
    worksheet.write(curr_row, 9, row['目标仓位'], fmt_percent)

# ----------------------------------------
# 第三部分：底部合计
# ----------------------------------------
total_row = start_row + len(df)
total_row_excel = total_row + 1

worksheet.write(total_row, 0, 'TOTAL', fmt_bold)
worksheet.write(total_row, 1, '合计', fmt_bold)

# F列合计 (总市值)
worksheet.write_formula(total_row, 5, f'=SUM(F8:F{total_row_excel-1})', fmt_currency)
# I列合计 (总仓位%)
worksheet.write_formula(total_row, 8, f'=SUM(I8:I{total_row_excel-1})', fmt_percent)
# J列合计 (目标%)
worksheet.write_formula(total_row, 9, f'=SUM(J8:J{total_row_excel-1})', fmt_percent)

# 设置列宽
worksheet.set_column('A:A', 10)
worksheet.set_column('B:B', 15)
worksheet.set_column('F:G', 12)

# 保存文件
writer.close()
print(f"成功生成文件: {file_name}")