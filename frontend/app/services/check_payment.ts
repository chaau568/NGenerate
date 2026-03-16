import { clientFetch } from "@/lib/client-fetch";

export type PaymentCheckingResponse = {
    payment_status: "pending" | "success" | "expired" | "failed";
};

export const checkPaymentStatus = async (
    transactionId: number
): Promise<PaymentCheckingResponse> => {
    const res = await clientFetch(
        `/api/package/checking?transaction_id=${transactionId}`
    );

    if (!res.ok) throw new Error("Failed to check payment");

    return res.json();
};