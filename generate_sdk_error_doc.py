from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path

OUT = Path(r'C:\Users\mahaishou\.openclaw\workspace\云侧SDK错误码上报技术需求文档.docx')

def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), fill)
    tcPr.append(shd)

def set_cell_text(cell, text, bold=False):
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(str(text))
    run.bold = bold
    run.font.name = '宋体'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
    run.font.size = Pt(10.5)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        set_cell_text(hdr[i], h, bold=True)
        set_cell_shading(hdr[i], 'D9EAF7')
        if widths:
            hdr[i].width = Inches(widths[i])
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            set_cell_text(cells[i], val)
            if widths:
                cells[i].width = Inches(widths[i])
    doc.add_paragraph('')
    return table


def add_heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = '黑体'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体')
    return p


def add_para(doc, text='', bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    if bold_prefix and text.startswith(bold_prefix):
        r = p.add_run(bold_prefix)
        r.bold = True
        r.font.name = '宋体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); r.font.size = Pt(10.5)
        rest = text[len(bold_prefix):]
        r2 = p.add_run(rest)
        r2.font.name = '宋体'; r2._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); r2.font.size = Pt(10.5)
    else:
        r = p.add_run(text)
        r.font.name = '宋体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); r.font.size = Pt(10.5)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.line_spacing = 1.2
        r = p.add_run(item)
        r.font.name = '宋体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); r.font.size = Pt(10.5)


doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.8)
sec.bottom_margin = Inches(0.8)
sec.left_margin = Inches(0.9)
sec.right_margin = Inches(0.9)

styles = doc.styles
styles['Normal'].font.name = '宋体'
styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
styles['Normal'].font.size = Pt(10.5)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('云侧 SDK 错误码上报技术需求文档')
r.bold = True
r.font.name = '黑体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '黑体'); r.font.size = Pt(18)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('版本：V1.0    适用对象：云侧 SDK / MediaEngine / CameraEngine / KBOX 相关模块')
r.font.name = '宋体'; r._element.rPr.rFonts.set(qn('w:eastAsia'), '宋体'); r.font.size = Pt(10.5)

doc.add_paragraph('')
add_heading(doc, '一、需求背景', 1)
add_para(doc, '当前云侧 SDK 在媒体建连、同屏共享、相机建连、消息/触控服务连接、KBOX 音视频模块启动等场景中已存在部分错误状态码，但错误码体系尚未完全统一，且部分异常仅在本地日志中体现，无法及时通过统一接口上报到后台，导致问题定位依赖人工排查日志，故障发现滞后，线上质量监控和运营分析能力不足。')
add_para(doc, '为提升云手机 SDK 的可观测性、故障定位效率和线上质量运营能力，需要由云侧 SDK 梳理各模块错误状态码，并在发生错误行为时，通过指定上报接口及时上报错误状态码及必要上下文信息。')

add_heading(doc, '二、需求目标', 1)
add_bullets(doc, [
    '建立统一的云侧 SDK 错误码规范，覆盖 MediaEngine、CameraEngine、KBOX 音视频模块、消息/触控服务、WebRTC 建连等关键链路。',
    '梳理已有错误码与新规范错误码之间的映射关系，避免现有业务逻辑大规模改造，同时保证后台统计口径统一。',
    '在发生参数错误、鉴权失败、建连失败、模块启动失败、媒体异常、资源异常等错误行为时，SDK 能够及时调用接口上报。',
    '上报信息应包含错误码、模块、错误类型、原始错误码、错误描述、会话标识、设备/实例信息、时间戳等，满足问题定位和统计分析。',
    '支持后续扩展更多监控项，如视频黑屏检测、音视频模块状态、系统资源占用、相机等待超时等。'
])

add_heading(doc, '三、需求范围', 1)
add_table(doc, ['范围', '说明'], [
    ['本次包含', '云侧 SDK 错误码规范、现有错误码映射、错误触发时机、错误上报字段、上报接口调用、失败重试/限频、日志留存、验收标准。'],
    ['本次不包含', '后台指标平台展示页面改造、告警策略配置、业务侧 UI 文案展示、端侧 SDK 错误码体系改造。'],
    ['涉及模块', 'MediaEngine、CameraEngine、KBOX 音频/视频/麦克风模块、消息服务、触控服务、WebRTC 建连链路、系统资源监控。'],
], widths=[1.4, 5.6])

add_heading(doc, '四、错误码规范', 1)
add_heading(doc, '4.1 错误码格式', 2)
add_para(doc, '统一错误码采用 5 位数字格式：XXYZZ。')
add_table(doc, ['段位', '含义', '数字范围', '示例', '说明'], [
    ['XX', '模块来源', '10-99', '40YZZ', '标识异常所属模块或业务域。'],
    ['Y', '错误类型', '0-9', 'XX2ZZ', '标识错误大类，如网络、认证、资源等。'],
    ['ZZ', '具体问题', '01-99', 'XXY01', '标识该错误类型下的具体问题或原因。'],
], widths=[0.8, 1.4, 1.0, 1.0, 2.8])

add_heading(doc, '4.2 模块来源定义', 2)
add_table(doc, ['XX', '模块', '职责说明'], [
    ['10', 'Android', '连接管理、显示异常、Android 端相关异常。'],
    ['11', 'H5', 'H5 页面、Web 容器相关异常。'],
    ['12', '鸿蒙', '鸿蒙端相关异常。'],
    ['13', 'PC', 'PC 端相关异常。'],
    ['14', 'iOS', 'iOS 端相关异常。'],
    ['15', '小程序', '小程序端相关异常。'],
    ['16', '云应用', '云应用启动、运行相关异常。'],
    ['20', '资管', '云机资源分配、token 分发等。'],
    ['21', '运管', '运维管控、实例管理等。'],
    ['30', '云 OS', '云机鉴权、系统能力、云 OS 运行相关异常。'],
    ['31', 'ARDC', '触控、消息、传感器通道相关异常。'],
    ['40', '端云协同', '媒体信令建立、音视频流管理、同屏共享、WebRTC 建连等。'],
], widths=[0.8, 1.4, 4.8])

add_heading(doc, '4.3 错误类型定义', 2)
add_table(doc, ['Y', '错误类型', '典型场景'], [
    ['0', '未知错误', '模块未捕获错误、兜底异常。'],
    ['1', '网络错误', 'TCP/UDP/WebRTC 连接超时、建连失败、服务断开。'],
    ['2', '认证鉴权错误', 'token 缺失、token 不匹配、token 过期。'],
    ['3', '资源错误', '云机不在线、连接数超限、端口不足、内存不足。'],
    ['4', '参数/协议错误', '请求 JSON 不合法、消息格式错误、字段缺失。'],
    ['5', '媒体流错误', '未收到 I 帧、黑屏、出流失败、音视频模块启动失败。'],
    ['6', '设备/通道错误', '相机、麦克风、传感器、触控/消息通道异常。'],
    ['7', '系统运行错误', 'CPU/内存过高、系统服务异常。'],
    ['8', '超时错误', '相机等待超时、麦克风注入超时、建连等待超时。'],
    ['9', '预留', '后续扩展使用。'],
], widths=[0.7, 1.6, 4.7])

add_heading(doc, '五、现有错误码梳理与新错误码映射', 1)
add_heading(doc, '5.1 MediaEngine 当前错误码', 2)
add_table(doc, ['源错误码', '描述', '备注', '建议统一错误码', '错误类型'], [
    ['2012', '参数错误', '请求 JSON 内容不合法。', '40401', '参数/协议错误'],
    ['2013', '服务器内部错误', '创建 client 对象失败，如内存不足、UDP 端口不足。', '40301', '资源错误'],
    ['2008', '同屏共享超过最大连接数', '同屏共享端进入，如老人机版本。', '40302', '资源错误'],
    ['1002', '主控不在线', '同屏共享进入且主控不在线。', '40303', '资源错误'],
    ['2014', '30 秒未建连成功', '收到 request 请求后 30 秒未建立 P2P 连接。', '40801', '超时错误'],
    ['2007', '建连后 8 秒内未收到 I 帧', '不断开连接，仅通知；可能 KBOX 启动失败或出流失败。', '40501', '媒体流错误'],
], widths=[0.9, 1.5, 2.5, 1.2, 1.2])

add_heading(doc, '5.2 CameraEngine 当前错误码', 2)
add_table(doc, ['源错误码', '描述', '备注', '建议统一错误码', '错误类型'], [
    ['10003', '连接消息服务失败', '消息服务连接失败。', '31101', '网络错误'],
    ['10004', '连接触控服务失败', '触控服务连接失败。', '31102', '网络错误'],
    ['10000', '解析 JSON 数据失败', '解析发往消息或触控服务的 JSON 数据失败。', '31401', '参数/协议错误'],
    ['10001', 'JSON 数据中未带 token', '请求缺少 token 字段。', '31201', '认证鉴权错误'],
    ['10002', 'token 不匹配', '请求 token 与服务侧校验不一致。', '31202', '认证鉴权错误'],
    ['10005', '消息服务或触控服务断开', '消息/触控服务连接中断。', '31103', '网络错误'],
], widths=[0.9, 1.7, 2.3, 1.2, 1.2])

add_heading(doc, '5.3 拟扩展监控项错误码', 2)
add_table(doc, ['模块', '监控项', '描述', '建议统一错误码', '触发条件'], [
    ['媒体服务', '音频模块状态', 'KBOX 音频模块启动状态和错误信息。', '40502', '音频模块启动失败或运行异常。'],
    ['媒体服务', '视频模块状态', 'KBOX 视频模块启动状态和错误信息。', '40503', '视频模块启动失败或出流异常。'],
    ['媒体服务', '麦克风模块状态', 'KBOX 麦克风模块启动状态和错误信息。', '40601', '麦克风模块启动失败或设备异常。'],
    ['媒体服务', '麦克风注入超时', '麦克风打开后 10 秒没有接收到数据。', '40802', '麦克风打开后 10 秒无数据注入。'],
    ['媒体服务', '视频黑屏检测', '黑屏检测信息，含出流码率大小。', '40504', '连续检测到黑屏或出流码率低于阈值。'],
    ['媒体服务', '系统资源监控', 'CPU、内存使用率。', '40701', 'CPU/内存超过配置阈值。'],
    ['相机服务', '相机建连超时', 'WebRTC 建连超时，8 秒未完成建连。', '40803', '相机 WebRTC 建连超过 8 秒。'],
    ['相机服务', '相机等待超时', '发送打开相机命令后，10 秒未注入数据。', '40804', '打开相机命令后 10 秒无数据注入。'],
    ['相机服务', '相机建连失败', 'WebRTC 建连失败。', '41104', 'WebRTC 建连失败或 ICE 状态失败。'],
], widths=[1.0, 1.4, 2.1, 1.1, 2.2])

add_heading(doc, '六、错误上报机制要求', 1)
add_heading(doc, '6.1 上报触发时机', 2)
add_bullets(doc, [
    'SDK 检测到明确错误行为时，应立即组装错误事件并调用上报接口。',
    '对于不会立即断开连接但会影响体验的异常，如 8 秒内未收到 I 帧、视频黑屏、码率异常，应以“告警类错误事件”上报。',
    '对于持续性异常，应避免高频重复上报，同一 session_id + error_code + module 在默认 60 秒内只上报一次，关键状态变化可再次上报。',
    '对于建连超时、鉴权失败、参数错误等一次性错误，应在错误返回或连接关闭前完成上报。',
    'SDK 本地日志应同步记录上报结果，包括上报成功、失败原因、重试次数。'
])

add_heading(doc, '6.2 上报事件字段', 2)
add_table(doc, ['字段名', '类型', '是否必填', '说明'], [
    ['appid', 'string', '是', '应用 ID，当前为 10244105。'],
    ['app_type', 'string', '是', '应用类型，固定为 Cloud_SDK。'],
    ['event_type', 'string', '是', '事件类型，建议固定为 sdk_error。'],
    ['error_code', 'string/int', '是', '统一错误码，格式 XXYZZ。'],
    ['source_error_code', 'string/int', '否', 'SDK 原始错误码，如 2012、10003。'],
    ['error_msg', 'string', '是', '错误提示语，如“参数错误”。'],
    ['error_reason', 'string', '否', '错误原因或详细描述，如“请求 JSON 内容不合法”。'],
    ['module', 'string', '是', '模块名称，如 MediaEngine、CameraEngine、KBOX。'],
    ['sub_module', 'string', '否', '子模块，如 audio、video、microphone、webrtc、message、touch。'],
    ['session_id', 'string', '建议必填', '会话标识，用于关联一次建连/同屏/相机会话。'],
    ['device_id', 'string', '否', '终端或云机设备标识，按现有埋点规范脱敏。'],
    ['instance_id', 'string', '否', '云机实例 ID 或资源实例标识。'],
    ['token_hash', 'string', '否', 'token 哈希值，仅用于排查，禁止上报明文 token。'],
    ['network_type', 'string', '否', '网络类型，如 Wi-Fi、4G、5G、unknown。'],
    ['timestamp', 'number/string', '是', '错误发生时间，建议毫秒时间戳。'],
    ['extra', 'object/string', '否', '扩展字段，如码率、CPU、内存、ICE 状态、端口信息等。'],
], widths=[1.4, 1.0, 0.8, 3.8])

add_heading(doc, '6.3 上报接口信息', 2)
add_table(doc, ['环境', '接口地址', 'appid', 'app_type', 'key'], [
    ['测试环境', 'https://uat-cloud.139.com/cloudphone/log/cloudphone/metrics', '10244105', 'Cloud_SDK', '7880fb6e1e2f419d87465d8ca2500361'],
    ['生产环境', 'https://cloud.139.com/cloudphone/log/cloudphone/metrics', '10244105', 'Cloud_SDK', 'f25ff67aa6634932a36cd508828c8a20'],
], widths=[0.9, 3.5, 0.9, 0.9, 1.8])
add_para(doc, '接口详细定义参照后台接口文档：https://s.apifox.cn/98860bf1-3d98-4039-abcc-d41fea34fb74/400810198e0')
add_para(doc, '安全要求：key 不应硬编码在公开仓库或客户端可直接反编译位置；如现有 SDK 需要内置 key，应通过配置中心、构建注入或服务端签名方式降低泄露风险。token 等敏感信息禁止明文上报。')

add_heading(doc, '6.4 上报示例', 2)
add_para(doc, '示例：MediaEngine 请求 JSON 内容不合法时，上报统一错误码 40401，并保留源错误码 2012。')
add_para(doc, '''{
  "appid": "10244105",
  "app_type": "Cloud_SDK",
  "event_type": "sdk_error",
  "module": "MediaEngine",
  "sub_module": "signaling",
  "error_code": "40401",
  "source_error_code": "2012",
  "error_msg": "参数错误",
  "error_reason": "请求JSON内容不合法",
  "session_id": "${session_id}",
  "timestamp": 1720000000000,
  "extra": {
    "request_type": "request",
    "sdk_version": "${sdk_version}"
  }
}''')

add_heading(doc, '七、功能性需求', 1)
add_table(doc, ['编号', '需求项', '优先级', '说明'], [
    ['FR-01', '错误码枚举维护', 'P0', 'SDK 内部维护统一错误码枚举及源错误码映射表，支持按模块查询。'],
    ['FR-02', '错误事件统一封装', 'P0', '提供统一 ErrorReporter 或 MetricsReporter 封装，业务模块仅需传入错误上下文。'],
    ['FR-03', '错误发生实时上报', 'P0', '在参数错误、鉴权失败、建连失败、资源不足、服务断开等场景发生时及时上报。'],
    ['FR-04', '媒体异常告警上报', 'P0', '8 秒未收到 I 帧、KBOX 音视频模块异常、黑屏、麦克风注入超时等需上报。'],
    ['FR-05', '上报失败重试', 'P1', '网络异常或接口失败时，支持本地短暂缓存和有限重试，避免阻塞主流程。'],
    ['FR-06', '重复事件限频', 'P1', '同一会话同一错误码短时间内去重，默认限频窗口 60 秒，可配置。'],
    ['FR-07', '本地日志留存', 'P1', '所有错误事件应写入 SDK 本地日志，便于接口不可用时离线排查。'],
    ['FR-08', '环境隔离配置', 'P0', '测试环境与生产环境接口、key 需要可配置，避免误上报。'],
    ['FR-09', '敏感信息脱敏', 'P0', 'token、手机号、用户标识等敏感信息不得明文上报。'],
], widths=[0.8, 1.6, 0.7, 3.9])

add_heading(doc, '八、非功能性需求', 1)
add_bullets(doc, [
    '性能：错误上报不得阻塞 SDK 主链路；建议异步队列上报，单次上报组包耗时控制在 5ms 内。',
    '可靠性：上报失败不影响原业务流程；重试次数建议不超过 3 次，超过后记录本地日志并丢弃或进入低优先级缓存。',
    '可扩展性：错误码映射表、限频时间、上报开关、环境配置应支持配置化。',
    '兼容性：保留源错误码字段，避免影响已有错误处理逻辑；统一错误码主要用于后台统计和跨模块分析。',
    '安全性：敏感字段脱敏；生产 key 妥善管理；上报接口使用 HTTPS。',
    '可观测性：后台可按 app_type、module、error_code、source_error_code、sdk_version、时间范围统计错误趋势。'
])

add_heading(doc, '九、验收标准', 1)
add_table(doc, ['编号', '验收项', '验收标准'], [
    ['AC-01', '错误码映射完整性', 'MediaEngine、CameraEngine 已梳理错误码均有对应统一错误码、提示语、原因说明。'],
    ['AC-02', '参数错误上报', '模拟请求 JSON 不合法，SDK 上报 error_code=40401，source_error_code=2012。'],
    ['AC-03', '建连超时上报', '模拟 P2P 30 秒未建连成功，SDK 上报 error_code=40801。'],
    ['AC-04', 'I 帧超时上报', '模拟建连后 8 秒未收到 I 帧，SDK 不断开连接但上报告警事件 error_code=40501。'],
    ['AC-05', '消息/触控服务异常上报', '模拟连接消息服务、触控服务失败或断开，SDK 分别上报对应错误码。'],
    ['AC-06', '鉴权异常上报', '模拟 token 缺失、token 不匹配，SDK 上报 31201、31202。'],
    ['AC-07', '限频生效', '同一 session 同一错误码 60 秒内重复触发时，仅上报一次或按配置限频。'],
    ['AC-08', '敏感信息检查', '上报内容中不存在明文 token、手机号等敏感信息。'],
    ['AC-09', '环境验证', '测试包上报到 UAT 接口，生产包上报到生产接口，不串环境。'],
], widths=[0.8, 1.8, 4.4])

add_heading(doc, '十、实施建议', 1)
add_bullets(doc, [
    '第一阶段：完成错误码规范确认、MediaEngine/CameraEngine 现有错误码映射、上报字段和接口联调。',
    '第二阶段：接入核心错误场景，包括参数错误、鉴权错误、建连超时、服务断开、I 帧超时。',
    '第三阶段：扩展 KBOX 音视频模块状态、麦克风注入超时、视频黑屏检测、系统资源监控等告警类事件。',
    '第四阶段：结合后台统计结果完善告警规则、错误码分布看板和问题闭环流程。'
])

add_heading(doc, '十一、待确认事项', 1)
add_table(doc, ['事项', '建议/待确认内容'], [
    ['错误码最终编码', '本文给出建议统一错误码，需云 SDK、后台、业务侧共同确认后冻结。'],
    ['接口字段格式', '需以 Apifox 接口定义为准，确认是否支持 extra 对象、批量上报、签名方式。'],
    ['限频策略', '默认 60 秒限频，需确认是否按错误等级区分。'],
    ['黑屏阈值', '需确认连续黑屏时长、码率阈值、是否结合帧率/关键帧判断。'],
    ['资源监控阈值', '需确认 CPU、内存阈值及采样周期。'],
    ['key 管理方式', '建议避免硬编码，需确认当前 SDK 构建和配置方案。'],
], widths=[1.6, 5.4])

add_heading(doc, '十二、附录：错误码总表', 1)
add_table(doc, ['统一错误码', '源错误码', '模块', '提示语', '原因/触发条件'], [
    ['40401', '2012', 'MediaEngine', '参数错误', '请求 JSON 内容不合法。'],
    ['40301', '2013', 'MediaEngine', '服务器内部错误', '创建 client 对象失败，如内存不足、UDP 端口不足。'],
    ['40302', '2008', 'MediaEngine', '同屏共享超过最大连接数', '同屏共享连接数达到上限。'],
    ['40303', '1002', 'MediaEngine', '主控不在线', '同屏共享进入且主控不在线。'],
    ['40801', '2014', 'MediaEngine', '建连超时', '收到 request 请求后 30 秒未建立 P2P 连接。'],
    ['40501', '2007', 'MediaEngine', '未收到 I 帧', '建连后 8 秒内未收到 I 帧，可能 KBOX 启动失败或出流失败。'],
    ['31101', '10003', 'CameraEngine', '连接消息服务失败', '消息服务连接失败。'],
    ['31102', '10004', 'CameraEngine', '连接触控服务失败', '触控服务连接失败。'],
    ['31401', '10000', 'CameraEngine', '解析 JSON 数据失败', '解析发往消息或触控服务的 JSON 数据失败。'],
    ['31201', '10001', 'CameraEngine', 'token 缺失', 'JSON 数据中未带 token。'],
    ['31202', '10002', 'CameraEngine', 'token 不匹配', 'token 校验不通过。'],
    ['31103', '10005', 'CameraEngine', '消息/触控服务断开', '消息服务或触控服务连接断开。'],
    ['40502', '-', '媒体服务', '音频模块异常', 'KBOX 音频模块启动失败或运行异常。'],
    ['40503', '-', '媒体服务', '视频模块异常', 'KBOX 视频模块启动失败或出流异常。'],
    ['40601', '-', '媒体服务', '麦克风模块异常', 'KBOX 麦克风模块启动失败或设备异常。'],
    ['40802', '-', '媒体服务', '麦克风注入超时', '麦克风打开后 10 秒没有接收到数据。'],
    ['40504', '-', '媒体服务', '视频黑屏', '连续检测到黑屏或出流码率异常。'],
    ['40701', '-', '媒体服务', '系统资源异常', 'CPU、内存使用率超过阈值。'],
    ['40803', '-', '相机服务', '相机建连超时', 'WebRTC 建连 8 秒未完成。'],
    ['40804', '-', '相机服务', '相机等待超时', '发送打开相机命令后 10 秒未注入数据。'],
    ['41104', '-', '相机服务', '相机建连失败', 'WebRTC 建连失败。'],
], widths=[1.0, 0.9, 1.1, 1.5, 3.0])

doc.save(OUT)
print(OUT)
