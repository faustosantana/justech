# -*- coding: utf-8 -*-
import json
from datetime import date
from odoo import Command
TOTAL=11800.0
company=env.company
customer=env["res.partner"].search([("customer_rank",">",0)],limit=1)
product=env["product.product"].search([("sale_ok","=",True)],limit=1)
tax_sale=env["account.tax"].search([("amount","=",18),("type_tax_use","=","sale"),("company_id","=",company.id)],limit=1)
journal_sale=env["account.journal"].search([("type","=","sale"),("company_id","=",company.id)],limit=1)
bnkd=env["account.journal"].search([("code","=","BNKD"),("company_id","=",company.id)],limit=1)
cat=env["hellenia.withholding.catalog"].search([("code","=","RET-GOB-5"),("company_id","=",company.id)],limit=1)
with env.cr.savepoint():
    i1=env["account.move"].create({"move_type":"out_invoice","partner_id":customer.id,"journal_id":journal_sale.id,"invoice_date":date.today(),"ref":"M07A","invoice_line_ids":[Command.create({"product_id":product.id,"quantity":1,"price_unit":10000.0,"tax_ids":[Command.set(tax_sale.ids)]})]}); i1.action_post()
    i2=env["account.move"].create({"move_type":"out_invoice","partner_id":customer.id,"journal_id":journal_sale.id,"invoice_date":date.today(),"ref":"M07B","invoice_line_ids":[Command.create({"product_id":product.id,"quantity":1,"price_unit":10000.0,"tax_ids":[Command.set(tax_sale.ids)]})]}); i2.action_post()
    wiz=env["hellenia.payment.partner.wizard"].create({"partner_type":"customer","partner_id":customer.id,"journal_id":bnkd.id,"payment_method_line_id":bnkd.inbound_payment_method_line_ids[:1].id})
    l1=wiz.line_ids.filtered(lambda l:l.move_id==i1)[:1]; l2=wiz.line_ids.filtered(lambda l:l.move_id==i2)[:1]
    l1.write({"apply":True,"amount_to_pay":TOTAL}); l2.write({"apply":True,"amount_to_pay":TOTAL,"withholding_catalog_ids":[Command.set(cat.ids)]})
    wiz.line_ids.filtered(lambda l:l.move_id not in (i1|i2)).write({"apply":False})
    sel=wiz.line_ids.filtered(lambda l:l.apply and l.amount_to_pay>0)
    wiz.action_register_payments()
    pay=env["account.payment"].search([("partner_id","=",customer.id)],order="id desc",limit=1)
    print("DIAG07:"+json.dumps({"selected":sel.mapped(lambda l: l.move_id.name),"pay":pay.name,"wh":pay.hellenia_withholding_total,"reconciled":pay.reconciled_invoice_ids.mapped("name"),"i1":i1.name,"i2":i2.name,"i1_in":i1 in pay.reconciled_invoice_ids,"i2_in":i2 in pay.reconciled_invoice_ids},default=str))
