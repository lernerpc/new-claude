# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, tools


class StudentSportPaymentReport(models.Model):
    _name = 'student.sport.payment.report'
    _description = 'Student Sport Payment Report'
    _auto = False
    _order = 'membership_month desc, student_id, activity_id'

    student_id = fields.Many2one('res.partner', string='Student', readonly=True)
    student_name = fields.Char(string='الطالب', readonly=True)
    activity_id = fields.Many2one('product.product', string='الرياضة/النشاط', readonly=True)
    activity_name = fields.Char(string='الرياضة/النشاط', readonly=True)
    membership_number = fields.Char(string='رقم الاستمارة', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    receipt_number = fields.Char(string='رقم الايصال (الفاتورة)', readonly=True)
    membership_month = fields.Char(string='الشهر', readonly=True)
    membership_month_select = fields.Selection(
        selection=[
            ('2024-01', 'يناير 2024'),
            ('2024-02', 'فبراير 2024'),
            ('2024-03', 'مارس 2024'),
            ('2024-04', 'إبريل 2024'),
            ('2024-05', 'مايو 2024'),
            ('2024-06', 'يونيو 2024'),
            ('2024-07', 'يوليو 2024'),
            ('2024-08', 'أغسطس 2024'),
            ('2024-09', 'سبتمبر 2024'),
            ('2024-10', 'أكتوبر 2024'),
            ('2024-11', 'نوفمبر 2024'),
            ('2024-12', 'ديسمبر 2024'),
            # add more as needed
        ],
        string='الشهر',
        readonly=True
    )
    payment_memo = fields.Char(string='رقم الايصال', readonly=True)
    payment_state = fields.Selection([
        ('not_paid', 'غير مدفوع'),
        ('paid', 'مدفوع'),
        ('partial', 'مدفوع جزئياً'),
        ('in_payment', 'قيد الدفع'),
    ], string='حالة الدفع', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f'''
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    ROW_NUMBER() OVER() AS id,
                    sa.student_id AS student_id,
                    rp.name AS student_name,
                    pp.id AS activity_id,
                    CASE
                        WHEN pt.name::text LIKE '%%{{%%' THEN
                            COALESCE(
                                pt.name::json->>'en_US',
                                pt.name::json->>'ar_SY',
                                pt.name::text
                            )
                        ELSE pt.name::text
                    END AS activity_name,
                    sa.membership_number AS membership_number,
                    am.id AS invoice_id,
                    am.ref AS receipt_number,
                    COALESCE(am.membership_fee_name,
                             TO_CHAR(am.invoice_date, 'YYYY-MM-DD'),
                             'N/A') AS membership_month,
                    TO_CHAR(am.invoice_date, 'YYYY-MM') AS membership_month_select,
                    COALESCE(payment.ref, 'لا يوجد ايصال') AS payment_memo,
                    CASE
                        WHEN am.payment_state = 'paid' THEN 'paid'
                        WHEN am.payment_state = 'partial' THEN 'partial'
                        WHEN am.payment_state = 'in_payment' THEN 'in_payment'
                        ELSE 'not_paid'
                    END AS payment_state
                FROM student_admission sa
                JOIN res_partner rp ON rp.id = sa.student_id
                JOIN product_product_student_admission_rel rel ON rel.student_admission_id = sa.id
                JOIN product_product pp ON rel.product_product_id = pp.id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                LEFT JOIN account_move am ON am.invoice_origin = sa.name
                    AND am.move_type = 'out_invoice'
                    AND am.state = 'posted'
                LEFT JOIN LATERAL (
                    SELECT ap.ref
                    FROM account_payment ap
                    JOIN account_move pm ON pm.id = ap.move_id
                    JOIN account_move_line pml ON pml.move_id = pm.id
                    JOIN account_partial_reconcile apr ON apr.credit_move_id = pml.id OR apr.debit_move_id = pml.id
                    JOIN account_move_line aml ON (apr.debit_move_id = aml.id OR apr.credit_move_id = aml.id)
                    WHERE aml.move_id = am.id
                    ORDER BY ap.id DESC
                    LIMIT 1
                ) payment ON TRUE
                WHERE sa.state IN ('enrolled', 'student')
                    AND pt.is_sportname = true
                GROUP BY
                    sa.student_id, rp.name, pp.id, pt.name, sa.membership_number,
                    am.id, am.ref, am.membership_fee_name, am.invoice_date, am.payment_state, payment.ref
            )
        ''')
