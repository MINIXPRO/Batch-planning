import inspect

def main():
    from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
    methods = [m for m in dir(PurchaseOrder) if not m.startswith("__")]
    print("Methods on PurchaseOrder:", methods)
    
    print("\n=== validate source ===")
    print(inspect.getsource(PurchaseOrder.validate))
    
    try:
        print("\n=== before_save source ===")
        print(inspect.getsource(PurchaseOrder.before_save))
    except Exception as e:
        print("No before_save or error:", e)

if __name__ == "__main__":
    main()
