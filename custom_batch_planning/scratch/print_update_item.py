import inspect

def main():
    from erpnext.stock.doctype.material_request.material_request import update_item
    print(inspect.getsource(update_item))

if __name__ == "__main__":
    main()
