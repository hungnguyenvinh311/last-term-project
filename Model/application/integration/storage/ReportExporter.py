import csv
from io import StringIO,BytesIO
from pathlib import Path
from Model.application.errors import DomainError


class ReportExporter:
    def export(self,report,format):
        if 'totals' in report:
            return self._export_inventory(report,format)
        headers=['articleID','productName','brand','categoryID','quantity','grossSales']
        if format=='csv':
            stream=StringIO(newline='');writer=csv.writer(stream)
            writer.writerow(['Period',str(report['start']),str(report['end'])])
            for key in ['orderCount','units','itemGrossSales','matchedOrdersNetMerchandise','matchedOrdersPaidAmount']:
                writer.writerow([key,str(report[key])])
            writer.writerow(['Scope',report['scope']]);writer.writerow(headers)
            for p in report['topProducts']:
                # Spreadsheet formula injection is possible even in quoted cells.
                writer.writerow([("'"+str(p[h])) if str(p[h]).lstrip().startswith(('=','+','-','@')) else str(p[h]) for h in headers])
            return ('\ufeff'+stream.getvalue()).encode('utf-8')
        if format!='pdf': raise DomainError('Định dạng không hợp lệ')
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import simpleSplit
        font='Helvetica'
        candidates=[Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
        for path in candidates:
            if path.is_file():
                if 'CommerceReport' not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont('CommerceReport',str(path)))
                font='CommerceReport';break
        out=BytesIO();c=canvas.Canvas(out,pagesize=(595,842));y=800
        lines=['Electra - Sales report',f"{report['start']} - {report['end']} (UTC+07:00 / VND)",report['scope']]
        lines += [f'{k}: {report[k]}' for k in ['orderCount','units','itemGrossSales','matchedOrdersNetMerchandise','matchedOrdersPaidAmount']]
        lines += [f"#{p['articleID']} | {p['productName']} | qty {p['quantity']} | {p['grossSales']} VND" for p in report['topProducts']]
        for line in lines:
            for part in simpleSplit(str(line),font,10,515):
                if y<45: c.showPage();y=800
                c.setFont(font,10);c.drawString(40,y,part);y-=15
            y-=6
        c.save();return out.getvalue()

    def _export_inventory(self,report,format):
        fields=['articleID','productName','brand','categoryID','openingQuantity','receivedInPeriod',
                'dispatchedInPeriod','adjustmentsInPeriod','closingQuantity','committedQuantity',
                'currentAvailableQuantity']
        if format=='csv':
            stream=StringIO(newline='');writer=csv.writer(stream)
            writer.writerow(['Period',str(report['start']),str(report['end'])])
            for key,value in report['totals'].items():writer.writerow([key,str(value)])
            writer.writerow(['Scope',report['scope']]);writer.writerow(fields)
            for product in report['products']:
                writer.writerow([("'"+str(product[field])) if str(product[field]).lstrip().startswith(('=','+','-','@')) else str(product[field]) for field in fields])
            return ('\ufeff'+stream.getvalue()).encode('utf-8')
        if format!='pdf':raise DomainError('Unsupported report format')
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import simpleSplit
        font='Helvetica'
        for path in [Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
            if path.is_file():
                if 'CommerceReport' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('CommerceReport',str(path)))
                font='CommerceReport';break
        out=BytesIO();c=canvas.Canvas(out,pagesize=(595,842));y=800
        lines=['Electra - Inventory report',f"{report['start']} - {report['end']} (UTC+07:00)",report['scope']]
        lines += [f'{key}: {value}' for key,value in report['totals'].items()]
        lines += [f"#{row['articleID']} | {row['productName']} | close {row['closingQuantity']} | available {row['currentAvailableQuantity']}" for row in report['products']]
        for line in lines:
            for part in simpleSplit(str(line),font,9,515):
                if y<45:c.showPage();y=800
                c.setFont(font,9);c.drawString(40,y,part);y-=14
            y-=5
        c.save();return out.getvalue()
