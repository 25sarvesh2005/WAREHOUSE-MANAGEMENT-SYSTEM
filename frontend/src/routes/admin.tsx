import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  CheckCircle2,
  PackagePlus,
  UserPlus,
  Ban,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { AiAuditPanel } from "@/components/AiAuditPanel";
import { ControlledLaunchPanel } from "@/components/ControlledLaunchPanel";
import { MigrationPanel } from "@/components/MigrationPanel";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { useAuth } from "@/lib/auth";
import {
  useApproveSellerMutation,
  useCreateProductMutation,
  useCreateUserMutation,
  useProductsQuery,
  useSellersQuery,
  useUpdateSellerStatusMutation,
  useUpdateUserStatusMutation,
  useUsersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { Product, Role, Seller, User, Warehouse } from "@/lib/types";

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "Admin Panel | Whitfield Ops" },
      {
        name: "description",
        content: "Manage users, roles, pending seller approvals, warehouses and products.",
      },
      { property: "og:title", content: "Admin Panel | Whitfield Ops" },
      {
        property: "og:description",
        content: "Administrator and Manager master data and staff hierarchy management.",
      },
    ],
  }),
  component: AdminPage,
});

const TABS = [
  "Users & Staff Hierarchy",
  "Pending Sellers",
  "Sellers",
  "Warehouses",
  "Products",
  "AI Audit & Provider Health",
  "Controlled Launch & Health",
  "Migration",
] as const;

type AdminTab = (typeof TABS)[number];

function AdminPage() {
  const { user, ready } = useAuth();
  const [tab, setTab] = useState<AdminTab>("Users & Staff Hierarchy");
  const isAdmin = user?.role === "ADMINISTRATOR";
  const isManager = user?.role === "WAREHOUSE_MANAGER" || isAdmin;
  const visibleTabs: readonly AdminTab[] = TABS;
  const activeTab = visibleTabs.includes(tab) ? tab : "Users & Staff Hierarchy";

  const usersQuery = useUsersQuery({ enabled: isManager });
  const sellersQuery = useSellersQuery({ enabled: isManager });
  const warehousesQuery = useWarehousesQuery({ enabled: isManager });
  const productsQuery = useProductsQuery(undefined, { enabled: isManager });
  const usersData = usersQuery.data ?? [];
  const sellers = sellersQuery.data ?? [];
  const warehouses = warehousesQuery.data ?? [];
  const products = productsQuery.data ?? [];

  const approveSellerMutation = useApproveSellerMutation();
  const updateUserStatusMutation = useUpdateUserStatusMutation();
  const updateSellerStatusMutation = useUpdateSellerStatusMutation();
  const createUserMutation = useCreateUserMutation();
  const createProductMutation = useCreateProductMutation();

  const [actionFeedback, setActionFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [updatingSellerId, setUpdatingSellerId] = useState<string | null>(null);

  const allUsers: Array<User & { created_by_name?: string | null }> = usersData;

  const pendingSellers = allUsers.filter(
    (u) => u.role === "SELLER" && (u.status === "PENDING_APPROVAL" || u.status === "INACTIVE"),
  );

  // Add User Modal State
  const [openAddUser, setOpenAddUser] = useState(false);
  const [openAddProduct, setOpenAddProduct] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "RECEIVER" as Role,
    warehouse_id: warehouses[0]?.id || "",
  });
  const [productForm, setProductForm] = useState({
    seller_id: "",
    sku: "",
    name: "",
    description: "",
    unit_of_measure: "EA",
    weight: "",
    length: "",
    width: "",
    height: "",
    status: "ACTIVE",
  });
  const [error, setError] = useState<string | null>(null);
  const [productError, setProductError] = useState<string | null>(null);

  if (ready && user && !isManager) {
    return (
      <AppShell>
        <div className="card-surface">
          <EmptyState
            message="Access Restricted"
            hint="Your role does not have user management privileges."
          />
        </div>
      </AppShell>
    );
  }

  async function handleApproveSeller(userId: string) {
    setActionFeedback(null);
    setUpdatingUserId(userId);
    try {
      await approveSellerMutation.mutateAsync(userId);
      setActionFeedback({
        type: "success",
        message: "Seller approved successfully! User and tenant status are now ACTIVE.",
      });
    } catch (err: unknown) {
      setActionFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to approve seller account.",
      });
    } finally {
      setUpdatingUserId(null);
    }
  }

  async function handleSetUserStatus(userId: string, newStatus: string) {
    setActionFeedback(null);
    setUpdatingUserId(userId);
    try {
      await updateUserStatusMutation.mutateAsync({ userId, status: newStatus });
      setActionFeedback({
        type: "success",
        message: `User status updated to ${newStatus} successfully.`,
      });
    } catch (err: unknown) {
      setActionFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to update user status.",
      });
    } finally {
      setUpdatingUserId(null);
    }
  }

  async function handleSetSellerStatus(sellerId: string, newStatus: string) {
    setActionFeedback(null);
    setUpdatingSellerId(sellerId);
    try {
      await updateSellerStatusMutation.mutateAsync({ sellerId, status: newStatus });
      setActionFeedback({
        type: "success",
        message: `Seller tenant status updated to ${newStatus} successfully.`,
      });
    } catch (err: unknown) {
      setActionFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to update seller status.",
      });
    } finally {
      setUpdatingSellerId(null);
    }
  }

  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.name.trim()) return setError("Name is required.");
    if (!form.email.includes("@")) return setError("Valid email required.");
    if (form.password.length < 8) return setError("Password must be at least 8 characters.");

    try {
      const targetWarehouse = form.warehouse_id || warehouses[0]?.id;
      await createUserMutation.mutateAsync({
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
        ...(targetWarehouse ? { warehouse_id: targetWarehouse } : {}),
      });
      setOpenAddUser(false);
      setForm({
        name: "",
        email: "",
        password: "",
        role: "RECEIVER",
        warehouse_id: warehouses[0]?.id || "",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create user.");
    }
  }

  async function handleCreateProduct(e: React.FormEvent) {
    e.preventDefault();
    setProductError(null);
    if (!productForm.seller_id) return setProductError("Seller is required.");
    if (!productForm.sku.trim()) return setProductError("SKU is required.");
    if (!productForm.name.trim()) return setProductError("Product name is required.");
    if (!productForm.unit_of_measure.trim()) return setProductError("Unit of measure is required.");

    const payload: Partial<Product> = {
      seller_id: productForm.seller_id,
      sku: productForm.sku.trim(),
      name: productForm.name.trim(),
      unit_of_measure: productForm.unit_of_measure.trim(),
      status: productForm.status,
    };
    if (productForm.description.trim()) payload.description = productForm.description.trim();
    if (productForm.weight) payload.weight = Number(productForm.weight);
    if (productForm.length) payload.length = Number(productForm.length);
    if (productForm.width) payload.width = Number(productForm.width);
    if (productForm.height) payload.height = Number(productForm.height);

    try {
      await createProductMutation.mutateAsync(payload);
      setOpenAddProduct(false);
      setProductForm({
        seller_id: "",
        sku: "",
        name: "",
        description: "",
        unit_of_measure: "EA",
        weight: "",
        length: "",
        width: "",
        height: "",
        status: "ACTIVE",
      });
    } catch (err: unknown) {
      setProductError(err instanceof Error ? err.message : "Failed to create product.");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Admin & Staff Hierarchy"
        subtitle="User access controls, seller approvals, and staff onboarding."
        actions={
          <>
            {isManager ? (
              <Button onClick={() => setOpenAddUser(true)}>
                <UserPlus className="size-4" /> Onboard Staff Member
              </Button>
            ) : null}
            {isAdmin && activeTab === "Products" ? (
              <Button variant="outline" onClick={() => setOpenAddProduct(true)}>
                <PackagePlus className="size-4" /> New Product
              </Button>
            ) : null}
          </>
        }
      />

      {actionFeedback ? (
        <div
          className={`mb-4 flex items-center justify-between rounded-xl border px-4 py-3 text-sm ${
            actionFeedback.type === "success"
              ? "border-status-green/30 bg-status-green/10 text-status-green"
              : "border-status-red/30 bg-status-red/10 text-status-red"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionFeedback.type === "success" ? (
              <CheckCircle2 className="size-4 shrink-0" />
            ) : (
              <AlertTriangle className="size-4 shrink-0" />
            )}
            <span>{actionFeedback.message}</span>
          </div>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-xs font-bold underline hover:opacity-80"
          >
            Dismiss
          </button>
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap gap-2">
        {visibleTabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`relative rounded-full border px-3.5 py-1.5 text-xs font-semibold transition-colors ${
              tab === t
                ? "border-primary bg-primary-tint text-primary"
                : "border-border text-muted-foreground hover:bg-muted"
            }`}
          >
            {t}
            {t === "Pending Sellers" && pendingSellers.length > 0 ? (
              <span className="ml-1.5 rounded-full bg-status-amber px-1.5 py-0.5 text-[10px] font-bold text-white">
                {pendingSellers.length}
              </span>
            ) : null}
          </button>
        ))}
      </div>

      {[usersQuery, sellersQuery, warehousesQuery, productsQuery].some((q) => q.isLoading) ? (
        <LoadingState />
      ) : null}
      {[usersQuery, sellersQuery, warehousesQuery, productsQuery].find((q) => q.isError) ? (
        <ErrorState
          message="Could not load admin data from the backend."
          onRetry={() => {
            usersQuery.refetch();
            sellersQuery.refetch();
            warehousesQuery.refetch();
            productsQuery.refetch();
          }}
        />
      ) : null}

      {activeTab === "Users & Staff Hierarchy" ? (
        <TableShell>
          <thead>
            <tr>
              <Th>Name</Th>
              <Th>Email</Th>
              <Th>Role</Th>
              <Th>Status</Th>
              <Th>Created By</Th>
              <Th className="text-right">Set Status / Actions</Th>
            </tr>
          </thead>
          <tbody>
            {allUsers.map((u) => (
              <tr key={u.id} className="hover:bg-primary-tint/40">
                <Td className="font-medium">{u.name}</Td>
                <Td className="text-muted-foreground">{u.email}</Td>
                <Td>
                  <span className="rounded-full bg-primary-tint px-2.5 py-1 text-xs font-semibold text-primary">
                    {u.role.replaceAll("_", " ")}
                  </span>
                </Td>
                <Td>
                  <StatusBadge value={u.status || "ACTIVE"} />
                </Td>
                <Td className="text-muted-foreground font-medium text-xs">
                  {u.created_by_name ||
                    (u.role === "ADMINISTRATOR" ? "System Superadmin" : "Alex Whitfield (Admin)")}
                </Td>
                <Td className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <select
                      value={u.status || "ACTIVE"}
                      disabled={updatingUserId === u.id || (!isAdmin && u.role === "ADMINISTRATOR")}
                      onChange={(e) => handleSetUserStatus(u.id, e.target.value)}
                      className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-semibold text-foreground outline-none focus:border-primary cursor-pointer disabled:opacity-50"
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="SUSPENDED">SUSPENDED</option>
                      <option value="INACTIVE">INACTIVE</option>
                      <option value="PENDING_APPROVAL">PENDING APPROVAL</option>
                    </select>
                    {updatingUserId === u.id ? (
                      <RefreshCw className="size-3.5 animate-spin text-primary" />
                    ) : null}
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </TableShell>
      ) : null}

      {activeTab === "Pending Sellers" ? (
        pendingSellers.length === 0 ? (
          <div className="card-surface">
            <EmptyState
              message="No pending seller registrations"
              hint="All seller accounts are currently reviewed."
            />
          </div>
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th>Merchant / Name</Th>
                <Th>Email</Th>
                <Th>Role</Th>
                <Th>Status</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {pendingSellers.map((u) => (
                <tr key={u.user_id || u.id} className="hover:bg-primary-tint/40">
                  <Td className="font-medium">{u.name}</Td>
                  <Td className="text-muted-foreground">{u.email}</Td>
                  <Td>
                    <span className="rounded-full bg-status-amber/20 px-2.5 py-1 text-xs font-semibold text-status-amber">
                      SELLER PENDING
                    </span>
                  </Td>
                  <Td>
                    <StatusBadge value={u.status || "PENDING_APPROVAL"} />
                  </Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        onClick={() => handleApproveSeller(u.id)}
                        disabled={updatingUserId === u.id}
                        className="py-1 px-3 text-xs bg-status-green hover:bg-status-green/90 text-white flex items-center gap-1"
                      >
                        {updatingUserId === u.id ? (
                          <RefreshCw className="size-3.5 animate-spin mr-1" />
                        ) : (
                          <CheckCircle2 className="size-3.5 mr-1" />
                        )}
                        Approve Seller
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => handleSetUserStatus(u.id, "SUSPENDED")}
                        disabled={updatingUserId === u.id}
                        className="py-1 px-2.5 text-xs text-status-red border-status-red/40 hover:bg-status-red/10 flex items-center gap-1"
                      >
                        <Ban className="size-3.5 mr-1" /> Reject
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </TableShell>
        )
      ) : null}

      {activeTab === "Sellers" ? (
        <TableShell>
          <thead>
            <tr>
              <Th>Code</Th>
              <Th>Merchant / Brand Name</Th>
              <Th>Contact Email</Th>
              <Th>Status</Th>
              <Th className="text-right">Set Status / Actions</Th>
            </tr>
          </thead>
          <tbody>
            {sellers.map((s: Seller) => (
              <tr key={s.id} className="hover:bg-primary-tint/40">
                <Td className="font-mono font-bold text-primary">{s.code}</Td>
                <Td className="font-medium">{s.name}</Td>
                <Td className="text-muted-foreground">{s.contact_email || "—"}</Td>
                <Td>
                  <StatusBadge value={s.status} />
                </Td>
                <Td className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <select
                      value={s.status || "ACTIVE"}
                      disabled={updatingSellerId === s.id}
                      onChange={(e) => handleSetSellerStatus(s.id, e.target.value)}
                      className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-semibold text-foreground outline-none focus:border-primary cursor-pointer disabled:opacity-50"
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="SUSPENDED">SUSPENDED</option>
                      <option value="INACTIVE">INACTIVE</option>
                    </select>
                    {updatingSellerId === s.id ? (
                      <RefreshCw className="size-3.5 animate-spin text-primary" />
                    ) : null}
                  </div>
                </Td>
              </tr>
            ))}
          </tbody>
        </TableShell>
      ) : null}

      {activeTab === "Warehouses" ? (
        <TableShell>
          <thead>
            <tr>
              <Th>Code</Th>
              <Th>Name</Th>
              <Th>City</Th>
              <Th>State</Th>
              <Th className="text-right">Utilization</Th>
            </tr>
          </thead>
          <tbody>
            {warehouses.map((w: Warehouse) => (
              <tr key={w.id} className="hover:bg-primary-tint/40">
                <Td className="font-medium">{w.code}</Td>
                <Td className="text-muted-foreground">{w.name}</Td>
                <Td>{w.city || "Reno"}</Td>
                <Td>{w.state || "NV"}</Td>
                <Td className="text-right">{w.utilization ?? 70}%</Td>
              </tr>
            ))}
          </tbody>
        </TableShell>
      ) : null}

      {activeTab === "Products" ? (
        <TableShell>
          <thead>
            <tr>
              <Th>SKU</Th>
              <Th>Name</Th>
              <Th>Seller</Th>
              <Th>UoM</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {products.map((p: Product) => (
              <tr key={p.id} className="hover:bg-primary-tint/40">
                <Td className="font-medium">{p.sku}</Td>
                <Td className="text-muted-foreground">{p.name}</Td>
                <Td>{sellers.find((seller) => seller.id === p.seller_id)?.code || p.seller_id}</Td>
                <Td>{p.unit_of_measure || "EACH"}</Td>
                <Td>
                  <StatusBadge value={p.status} />
                </Td>
              </tr>
            ))}
          </tbody>
        </TableShell>
      ) : null}

      {activeTab === "AI Audit & Provider Health" ? <AiAuditPanel /> : null}
      {activeTab === "Controlled Launch & Health" ? <ControlledLaunchPanel /> : null}
      {activeTab === "Migration" ? <MigrationPanel /> : null}

      {/* Modal to Register Staff according to RBAC */}
      {openAddUser ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 px-4">
          <Card className="w-full max-w-md p-6">
            <h2 className="font-semibold text-navy">Onboard Staff Member</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {isAdmin
                ? "As an Administrator, you can onboard Managers, Receivers, and Pickers."
                : "As a Warehouse Manager, you can onboard Receivers and Pickers."}
            </p>
            {error ? (
              <p className="mt-3 rounded-xl border border-status-red/30 bg-status-red/5 px-3 py-2 text-sm text-status-red">
                {error}
              </p>
            ) : null}
            <form onSubmit={handleCreateUser} className="mt-4 space-y-3 text-sm">
              <label className="block">
                <span className="font-medium">Role</span>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                >
                  {isAdmin && <option value="WAREHOUSE_MANAGER">Warehouse Manager</option>}
                  <option value="RECEIVER">Receiver (Inbound Dock)</option>
                  <option value="PICKER_PACKER">Picker / Packer (Fulfillment)</option>
                </select>
              </label>
              <label className="block">
                <span className="font-medium">Full Name</span>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Jordan Vance"
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <label className="block">
                <span className="font-medium">Email</span>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="jordan@whitfield.local"
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <label className="block">
                <span className="font-medium">Temporary Password</span>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <label className="block">
                <span className="font-medium">Assigned Warehouse</span>
                <select
                  value={form.warehouse_id}
                  onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                >
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({w.code})
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-5 flex justify-end gap-2">
                <Button variant="ghost" type="button" onClick={() => setOpenAddUser(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createUserMutation.isPending}>
                  {createUserMutation.isPending ? "Onboarding..." : "Register Staff"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      ) : null}

      {openAddProduct ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/40 px-4">
          <Card className="w-full max-w-2xl p-6">
            <h2 className="font-semibold text-navy">Create Product / SKU</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Product master data is tenant-scoped to a seller and defaults to active status.
            </p>
            {productError ? (
              <p className="mt-3 rounded-xl border border-status-red/30 bg-status-red/5 px-3 py-2 text-sm text-status-red">
                {productError}
              </p>
            ) : null}
            <form onSubmit={handleCreateProduct} className="mt-4 grid gap-3 text-sm md:grid-cols-2">
              <label className="block">
                <span className="font-medium">Seller</span>
                <select
                  value={productForm.seller_id}
                  onChange={(e) => setProductForm({ ...productForm, seller_id: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                >
                  <option value="">Select seller</option>
                  {sellers.map((seller) => (
                    <option key={seller.id} value={seller.id}>
                      {seller.code} - {seller.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="font-medium">Status</span>
                <select
                  value={productForm.status}
                  onChange={(e) => setProductForm({ ...productForm, status: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                >
                  <option value="ACTIVE">Active</option>
                  <option value="INACTIVE">Inactive</option>
                </select>
              </label>
              <label className="block">
                <span className="font-medium">SKU</span>
                <input
                  required
                  value={productForm.sku}
                  onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <label className="block">
                <span className="font-medium">Name</span>
                <input
                  required
                  value={productForm.name}
                  onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <label className="block">
                <span className="font-medium">Unit of measure</span>
                <input
                  required
                  value={productForm.unit_of_measure}
                  onChange={(e) =>
                    setProductForm({ ...productForm, unit_of_measure: e.target.value })
                  }
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <label className="block">
                <span className="font-medium">Weight</span>
                <input
                  type="number"
                  min="0"
                  value={productForm.weight}
                  onChange={(e) => setProductForm({ ...productForm, weight: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <div className="grid grid-cols-3 gap-3 md:col-span-2">
                <label className="block">
                  <span className="font-medium">Length</span>
                  <input
                    type="number"
                    min="0"
                    value={productForm.length}
                    onChange={(e) => setProductForm({ ...productForm, length: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                  />
                </label>
                <label className="block">
                  <span className="font-medium">Width</span>
                  <input
                    type="number"
                    min="0"
                    value={productForm.width}
                    onChange={(e) => setProductForm({ ...productForm, width: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                  />
                </label>
                <label className="block">
                  <span className="font-medium">Height</span>
                  <input
                    type="number"
                    min="0"
                    value={productForm.height}
                    onChange={(e) => setProductForm({ ...productForm, height: e.target.value })}
                    className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                  />
                </label>
              </div>
              <label className="block md:col-span-2">
                <span className="font-medium">Description</span>
                <textarea
                  value={productForm.description}
                  onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                  rows={3}
                  className="mt-1 w-full rounded-xl border border-border bg-card px-3 py-2 outline-none focus:border-primary"
                />
              </label>
              <div className="mt-2 flex justify-end gap-2 md:col-span-2">
                <Button variant="ghost" type="button" onClick={() => setOpenAddProduct(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createProductMutation.isPending}>
                  {createProductMutation.isPending ? "Creating..." : "Create Product"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      ) : null}
    </AppShell>
  );
}
