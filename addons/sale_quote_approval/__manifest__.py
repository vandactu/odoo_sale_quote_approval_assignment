{
    "name": "Sale Quote Approval",
    "version": "18.0.1.0.0",
    "summary": "Multi-level approval workflow for quotations based on cost margin",
    "author": "Interview Assignment",
    "depends": ["sale_management"],
    "data": [
        # ============================== SECURITY =============================
        "security/security.xml",

        # ============================== VIEWS ================================
        "views/sale_order_views.xml"
    ],
    "installable": True,
    'assets': {
        'web.assets_backend': [
            'sale_quote_approval/static/src/components/**/*',
        ],
    },
}
