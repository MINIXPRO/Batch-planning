import inspect
from erpnext.stock.utils import get_stock_balance

def run():
    print(inspect.getsource(get_stock_balance))
