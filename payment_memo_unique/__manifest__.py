{
    'name': 'Payment Memo Unique - رقم الايصال',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Make payment memo field unique with Arabic label',
    'description': '''
        This module:
        - Changes the payment memo field label to "رقم الايصال" (Receipt Number)
        - Makes the memo field unique for new payments
        - Allows existing duplicate memos to remain (grandfathered)
        - Prevents creation of new duplicate memo numbers
    ''',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['account'],
    'data': [
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
