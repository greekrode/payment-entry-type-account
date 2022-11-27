import frappe
from frappe import _
from frappe.utils import (
    formatdate
)
from erpnext.accounts.utils import get_account_currency, get_fiscal_years
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
)
from erpnext.accounts.general_ledger import (
    process_gl_map,
    make_gl_entries
)


def setup(payment_entry_type_account, method):
    # add expenses up and set the total field
    # add default project and cost center to expense items

    total = 0
    count = 0
    expense_items = []

    for detail in payment_entry_type_account.expenses:
        total += float(detail.amount)
        count += 1

        if not detail.project and payment_entry_type_account.default_project:
            detail.project = payment_entry_type_account.default_project

        if not detail.cost_center and payment_entry_type_account.default_cost_center:
            detail.cost_center = payment_entry_type_account.default_cost_center

        expense_items.append(detail)

    payment_entry_type_account.expenses = expense_items

    payment_entry_type_account.total = total
    payment_entry_type_account.quantity = count

    if payment_entry_type_account.status == "Approved":
        gl_entries = build_gl_map(payment_entry_type_account)
        gl_entries = process_gl_map(gl_entries, merge_entries=False)
        make_gl_entries(gl_entries, cancel=0, adv_adj=False,
                        merge_entries=False, update_outstanding="No")


@frappe.whitelist()
def build_gl_map(payment_entry_type_account, cancel=0):
    # check for duplicates

    if frappe.db.exists({'doctype': 'Journal Entry', 'bill_no': payment_entry_type_account.name}):
        frappe.throw(
            title="Error",
            msg="Journal Entry {} already exists.".format(
                payment_entry_type_account.name)
        )

    # Preparing the JE: convert payment_entry_type_account details into je account details

    gl_entries = []

    if payment_entry_type_account.payment_type == "Pay":
        gl_entries.append(
            get_gl_dict(
                payment_entry_type_account,
                {
                    'account': payment_entry_type_account.payment_account,
                    'account_currency': payment_entry_type_account.payment_account_currency,
                    'credit_in_account_currency': float(payment_entry_type_account.total),
                    'credit': float(payment_entry_type_account.total),
                    'cost_center': payment_entry_type_account.default_cost_center,
                    "post_net_value": True,
                },
                item=payment_entry_type_account,
            )
        )

    if payment_entry_type_account.payment_type == "Receive":
        gl_entries.append(
            get_gl_dict(
                payment_entry_type_account,
                {
                    'account': payment_entry_type_account.payment_account,
                    'account_currency': payment_entry_type_account.payment_account_currency,
                    'debit_in_account_currency': float(payment_entry_type_account.total),
                    'debit': float(payment_entry_type_account.total),
                    'cost_center': payment_entry_type_account.default_cost_center,
                },
                item=payment_entry_type_account,
            )
        )
    for detail in payment_entry_type_account.expenses:
        if payment_entry_type_account.payment_type == "Receive":
            gl_entries.append(
                get_gl_dict(
                    payment_entry_type_account,
                    {
                        'account': detail.expense_account,
                        'account_currency': payment_entry_type_account.payment_account_currency,
                        'credit_in_account_currency': float(detail.amount),
                        'credit': float(detail.amount),
                        'cost_center': payment_entry_type_account.default_cost_center,
                        "post_net_value": True,
                    },
                    item=payment_entry_type_account,
                )
            )

        if payment_entry_type_account.payment_type == "Pay":
            gl_entries.append(
                get_gl_dict(
                    payment_entry_type_account,
                    {
                        'account': detail.expense_account,
                        'account_currency': payment_entry_type_account.payment_account_currency,
                        'debit_in_account_currency': float(detail.amount),
                        'debit': float(detail.amount),
                        'cost_center': payment_entry_type_account.default_cost_center
                    },
                    item=payment_entry_type_account,
                )
            )
    # finally add the payment account detail
    return gl_entries


def get_gl_dict(self, args, item=None):
    """this method populates the common properties of a gl entry record"""

    posting_date = args.get("posting_date") or self.get("posting_date")
    fiscal_years = get_fiscal_years(posting_date, company=self.company)
    if len(fiscal_years) > 1:
        frappe.throw(
            _("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(
                formatdate(posting_date)
            )
        )
    else:
        fiscal_year = fiscal_years[0][0]

    gl_dict = frappe._dict(
        {
            "company": self.company,
            "posting_date": posting_date,
            "fiscal_year": fiscal_year,
            "voucher_type": self.doctype,
            "voucher_no": self.name,
            "remarks": self.get("remarks") or self.get("remark"),
            "debit": 0,
            "credit": 0,
            "debit_in_account_currency": 0,
            "credit_in_account_currency": 0,
            "is_opening": self.get("is_opening") or "No",
            "party_type": None,
            "party": None,
            "project": self.get("project"),
            "post_net_value": args.get("post_net_value"),
        }
    )

    accounting_dimensions = get_accounting_dimensions()
    dimension_dict = frappe._dict()

    for dimension in accounting_dimensions:
        dimension_dict[dimension] = self.get(dimension)
        if item and item.get(dimension):
            dimension_dict[dimension] = item.get(dimension)

    gl_dict.update(dimension_dict)
    gl_dict.update(args)

    return gl_dict
