import sys

from PyQt6.QtWidgets import QApplication

from app.ui.product.controllers.product_management_controller import (
    ProductManagementController
)


def main():

    app = QApplication(sys.argv)

    window = ProductManagementController()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":

    main()