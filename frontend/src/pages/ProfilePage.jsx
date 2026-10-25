import React, { useState } from 'react';
import {
  User,
  Mail,
  Phone,
  Shield,
  KeyRound,
  Calendar,
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { usersApi } from '../api/users';
import { RoleBadge } from '../components/common/Badge';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { SuccessAlert } from '../components/common/SuccessAlert';
import { getErrorMessage } from '../api/client';

export const ProfilePage = () => {
  const { user, updateUser } = useAuth();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setIsUpdatingProfile(true);

    try {
      const updated = await usersApi.updateMe({
        full_name: fullName,
        phone: phone || undefined,
      });
      updateUser(updated);
      setSuccess('Profile information updated successfully.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleUpdatePassword = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await usersApi.updateMe({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSuccess('Account password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Account & Security Profile</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Manage your verified account credentials, contact information, and role privileges.
        </p>
      </div>

      {success && <SuccessAlert message={success} onClose={() => setSuccess(null)} />}
      {error && <ErrorAlert message={error} onClose={() => setError(null)} />}

      {/* Overview Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-black text-xl uppercase shadow-md shadow-indigo-200">
            {user?.username?.substring(0, 2) || 'US'}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-slate-900">{user?.username}</h2>
              <RoleBadge role={user?.role} />
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{user?.email}</p>
            <div className="flex items-center space-x-4 mt-2 text-[11px] text-slate-400">
              <span className="flex items-center">
                <Calendar className="w-3.5 h-3.5 mr-1" />
                Joined {new Date(user?.created_at || Date.now()).toLocaleDateString()}
              </span>
              <span className="flex items-center">
                <Shield className="w-3.5 h-3.5 mr-1 text-emerald-500" />
                Status: <span className="font-semibold text-emerald-600 ml-1">{user?.status}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Update Contact Info */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center">
            <User className="w-4 h-4 text-indigo-600 mr-2" />
            Personal Details
          </h3>

          <form onSubmit={handleUpdateProfile} className="space-y-3 text-xs">
            <div>
              <label htmlFor="profile-full-name" className="block font-semibold text-slate-700 mb-1">Full Legal / Display Name</label>
              <input
                id="profile-full-name"
                type="text"
                autoComplete="name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <div>
              <label htmlFor="profile-phone" className="block font-semibold text-slate-700 mb-1">Phone Number</label>
              <input
                id="profile-phone"
                type="tel"
                autoComplete="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 555-0199"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={isUpdatingProfile}
              className="mt-2 w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50"
            >
              {isUpdatingProfile ? 'Saving...' : 'Save Profile Changes'}
            </button>
          </form>
        </div>

        {/* Change Password */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center">
            <KeyRound className="w-4 h-4 text-indigo-600 mr-2" />
            Security Credentials
          </h3>

          <form onSubmit={handleUpdatePassword} className="space-y-3 text-xs">
            <div>
              <label htmlFor="profile-current-password" className="block font-semibold text-slate-700 mb-1">Current Password</label>
              <input
                id="profile-current-password"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <div>
              <label htmlFor="profile-new-password" className="block font-semibold text-slate-700 mb-1">New Password (Min 8 chars)</label>
              <input
                id="profile-new-password"
                type="password"
                autoComplete="new-password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={isUpdatingPassword}
              className="mt-2 w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-bold transition-colors disabled:opacity-50"
            >
              {isUpdatingPassword ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
