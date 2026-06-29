import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@/App.css";
import { AuthProvider, useAuth } from "@/lib/auth";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import Keywords from "@/pages/Keywords";
import Findings from "@/pages/Findings";
import Billing from "@/pages/Billing";
import Admin from "@/pages/Admin";
import Documents from "@/pages/Documents";
import Security from "@/pages/Security";

const Protected = ({ children, admin = false }) => {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-white"><span className="font-mono">LOADING<span className="blink">_</span></span></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && !user.is_admin) return <Navigate to="/dashboard" replace />;
  return children;
};

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
            <Route path="/keywords" element={<Protected><Keywords /></Protected>} />
            <Route path="/findings" element={<Protected><Findings /></Protected>} />
            <Route path="/billing" element={<Protected><Billing /></Protected>} />
            <Route path="/documents" element={<Protected><Documents /></Protected>} />
            <Route path="/security" element={<Protected><Security /></Protected>} />
            <Route path="/admin" element={<Protected admin><Admin /></Protected>} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </div>
  );
}

export default App;
