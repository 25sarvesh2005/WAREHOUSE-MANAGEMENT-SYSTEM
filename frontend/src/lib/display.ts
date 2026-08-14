import type {
  EventLogEntry,
  LineItem,
  Movement,
  Order,
  PickTaskLine,
  Product,
  ReceiptEvent,
  ReceiptLine,
  ReturnLine,
  Seller,
  TransferLine,
  Warehouse,
} from "./types";

export function sellerLabel(sellers: Seller[], id?: string | null): string {
  const seller = sellers.find((item) => item.id === id);
  return seller ? seller.code : id || "SELLER";
}

export function warehouseLabel(warehouses: Warehouse[], id?: string | null): string {
  const warehouse = warehouses.find((item) => item.id === id);
  return warehouse ? warehouse.code : id || "WAREHOUSE";
}

export function productSku(products: Product[], id?: string | null): string {
  const product = products.find((item) => item.id === id);
  return product ? product.sku : id || "SKU";
}

export function productName(products: Product[], id?: string | null): string {
  const product = products.find((item) => item.id === id);
  return product ? product.name : id || "Product";
}

export function orderDestination(order: Order): string {
  return (
    [order.city, order.state].filter(Boolean).join(", ") ||
    order.shipping_address_line1 ||
    "Standard shipping"
  );
}

export function toReceiptLineItem(line: ReceiptLine, products: Product[]): LineItem {
  return {
    id: line.id,
    sku: productSku(products, line.product_id),
    product_name: productName(products, line.product_id),
    quantity: line.expected_quantity,
    note: line.notes,
  };
}

export function toTransferLineItem(line: TransferLine, products: Product[]): LineItem {
  return {
    id: line.id,
    sku: productSku(products, line.product_id),
    product_name: productName(products, line.product_id),
    quantity: line.requested_quantity,
    note: line.notes,
  };
}

export function toReturnLineItem(line: ReturnLine, products: Product[]): LineItem {
  return {
    id: line.id,
    sku: productSku(products, line.product_id),
    product_name: productName(products, line.product_id),
    quantity: line.received_quantity || line.expected_quantity,
    note: line.inspection_notes || line.reason_code,
  };
}

export function toPickTaskLineItem(line: PickTaskLine, products: Product[]): LineItem {
  return {
    id: line.id,
    sku: productSku(products, line.product_id),
    product_name: productName(products, line.product_id),
    quantity: line.requested_quantity,
  };
}

export function toReceiptEvent(event: ReceiptEvent): EventLogEntry {
  return {
    id: event.id,
    at: event.created_at,
    label: event.event_type.replaceAll("_", " "),
    detail: event.details || "Receipt event recorded.",
  };
}

export function movementActivity(movement: Movement): EventLogEntry {
  return {
    id: movement.id,
    at: movement.occurred_at,
    label: movement.movement_type.replaceAll("_", " "),
    detail: `${movement.inventory_state} ${movement.quantity_delta} units`,
  };
}
