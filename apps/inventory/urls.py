from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventoryOverviewView.as_view(), name="overview"),
    path("movements/", views.StockMovementListView.as_view(), name="movement_list"),
    path("movements/add/", views.StockMovementCreateView.as_view(), name="movement_create"),
    path("reports/low-stock/", views.LowStockReportView.as_view(), name="low_stock_report"),
    path("reports/out-of-stock/", views.OutOfStockReportView.as_view(), name="out_of_stock_report"),
    path("reports/expired/", views.ExpiredStockReportView.as_view(), name="expired_report"),
    path("batches/", views.BatchListView.as_view(), name="batch_list"),
    # Full inventory management
    path("ledger/", views.StockLedgerView.as_view(), name="ledger"),
    path("stocktakes/", views.StockTakeListView.as_view(), name="stocktake_list"),
    path("stocktakes/start/", views.StockTakeStartView.as_view(), name="stocktake_start"),
    path("stocktakes/<int:pk>/", views.StockTakeDetailView.as_view(), name="stocktake_detail"),
    path("stocktakes/<int:pk>/save/", views.StockTakeSaveCountsView.as_view(), name="stocktake_save"),
    path("stocktakes/<int:pk>/post/", views.StockTakePostView.as_view(), name="stocktake_post"),
    path("stocktakes/<int:pk>/cancel/", views.StockTakeCancelView.as_view(), name="stocktake_cancel"),
    path("reorder/", views.ReorderPlanView.as_view(), name="reorder_plan"),
    path("aging/", views.StockAgingView.as_view(), name="aging"),
]
