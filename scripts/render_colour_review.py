import sys,json,html,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from Model.application.config.settings import ROOT

def main():
    entries=json.loads((ROOT/'data/retailer_catalog/color_annotations.json').read_text(encoding='utf-8'))
    out=ROOT/'data/evaluation/colour_review';out.mkdir(parents=True,exist_ok=True)
    pending=[e for e in entries if e['status']=='needs_user_review']
    cards=[]
    for e in pending+[e for e in entries if e not in pending]:
        image=os.path.relpath(ROOT/e['imagePath'],out).replace('\\','/')
        colour=e['colour'] or 'CHƯA XÁC ĐỊNH — không áp dụng bộ lọc màu'
        status='Cần kiểm tra' if not e['colour'] else 'Quan sát từ ảnh bởi trợ lý'
        cards.append(f'<article><img src="{html.escape(image)}"><div><h3>#{e["articleID"]}: {html.escape(e["productName"])}</h3><b>{html.escape(colour)}</b><p>{status}</p><p>Phạm vi: {html.escape(e["scope"])}</p><small>{html.escape(e["notes"])}</small></div></article>')
    page='<!doctype html><meta charset="utf-8"><title>Kiểm tra màu ảnh sản phẩm</title><style>body{font:15px system-ui;max-width:1150px;margin:30px auto}article{display:flex;gap:24px;border:1px solid #ddd;margin:12px 0;padding:18px}img{width:220px;height:210px;object-fit:contain}small{color:#666}</style>'
    page+=f'<h1>Màu ảnh đại diện: {len(entries)-len(pending)} đã quan sát, {len(pending)} cần kiểm tra</h1><p>Màu của thân sản phẩm; với đồng hồ là màu dây nhìn thấy. Bỏ qua hình nền màn hình, chữ quảng cáo và chấm màu phiên bản. Đây không phải thông tin xác nhận mọi màu cửa hàng đang bán. Các mục chưa rõ được đặt đầu danh sách.</p>'
    (out/'index.html').write_text(page+''.join(cards),encoding='utf-8')
    (out/'pending.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Colour review page created; unresolved IDs: '+', '.join(str(e['articleID']) for e in pending))

if __name__=='__main__':main()
