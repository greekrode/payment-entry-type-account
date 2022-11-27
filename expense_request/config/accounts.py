from __future__ import unicode_literals
from frappe import _
import frappe


def get_data():
	config = [
		
		{
			"label": _("General Ledger"),
			"items": [
				{
					"type": "doctype",
					"name": "Payment Entry Type Account",
					"description": _("Capture Expenses"),
            		"link": "List/Payment Entry Type Account/Link"
				}
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Expenses Register",
					"doctype": "Payment Entry Type Account",
            		"link": "List/Payment Entry Type Account/Report/Expenses Register"
					
				}
			]
		}

	]
	return config
