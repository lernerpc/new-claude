{
    'name': "Sports Center Membership Fees",
    'summary': "Manage first month extra fees for sports center memberships",
    'depends': ['bi_sport_center_management', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/membership_fees_views.xml',
        'data/sequences.xml',
    ],
    'demo': [],  # Empty or remove this line completely

}
