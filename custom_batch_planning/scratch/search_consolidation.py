import inspect

def main():
    from erpnext.buying.doctype.purchase_order.purchase_order import PurchaseOrder
    # Let's inspect all methods of PurchaseOrder class to see if any relates to consolidation
    methods = [m for m in dir(PurchaseOrder) if not m.startswith("__")]
    print("Methods on PurchaseOrder:", methods)
    
    # Check if there is an onload or before_save or validate consolidation
    # Let's read source code of validate
    print("\n=== validate source ===")
    print(inspect.getsource(PurchaseOrder.validate))
    
    try:
        print("\n=== before_save source ===")
        print(inspect.getsource(PurchaseOrder.before_save))
    except Exception as e:
        print("No before_save or error:", e)

if __name__ == "__main__":
    main()
