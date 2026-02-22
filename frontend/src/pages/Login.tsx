import React from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import Cookies from 'js-cookie';
import { toast } from 'sonner';
import api from '../api/axiosInstance';
import type { LoginResponse, LoginError } from '../types/auth';

const Login = () => {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const navigate = useNavigate();

  const onSubmit = async (data: any) => {
    try {
      const res = await api.post<LoginResponse>('/user/login/', data);
      
      // เก็บ Token ใน Cookies
      Cookies.set('access', res.data.access);
      Cookies.set('refresh', res.data.refresh);
      
      toast.success('Login Successful!');
      navigate('/library'); // Redirect ไปหน้า library
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Invalid credentials';
      toast.error(errorMsg);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-primary p-4 font-roboto">
      <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md">
        <div className="flex flex-col items-center mb-6">
          <div className="w-12 h-12 border-4 border-[#1A9FD4] flex items-center justify-center text-[#1A9FD4] font-bold text-2xl mb-2">
            N
          </div>
          <h1 className="text-2xl font-bold text-primary">Login</h1>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input 
              {...register('email', { required: true })}
              type="email" 
              className="mt-1 block w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-md focus:outline-none focus:ring-secondary focus:border-secondary text-primary"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input 
              {...register('password', { required: true })}
              type="password" 
              className="mt-1 block w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-md focus:outline-none focus:ring-secondary focus:border-secondary text-primary"
            />
          </div>

          <button 
            type="submit" 
            className="w-full py-2 px-4 bg-secondary hover:bg-[#1589b8] text-white font-bold rounded-md transition duration-200"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;