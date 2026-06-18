import inspect

def main():
    from erpnext.stock.doctype.material_request.material_request import make_purchase_order
    print(inspect.getsource(make_purchase_order))
