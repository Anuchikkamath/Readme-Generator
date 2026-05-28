import { useAuth } from '../contexts/AuthContext';

export default function useAuthHook() {
    return useAuth();
}
