export interface LoginResponse {
    access: string;
    refresh: string;
}

export interface LoginError {
    error: string;
}