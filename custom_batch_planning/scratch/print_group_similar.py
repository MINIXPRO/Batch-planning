import inspect

def main():
    from erpnext.controllers.accounts_controller import AccountsController
    print(inspect.getsource(AccountsController.group_similar_items))

if __name__ == "__main__":
    main()
