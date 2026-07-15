import frappe
import inspect
from erpnext.stock.stock_ledger import make_entry

def run():
    print(inspect.getsource(make_entry))
