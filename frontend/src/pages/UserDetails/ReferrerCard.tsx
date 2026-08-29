import type { User } from '@/types';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { UserDetailsCard } from '../JobDetails/UserDetailsCard';

export const ReferrerCard: React.FC<{
  referrerId: string | null | undefined;
}> = ({ referrerId }) => {
  const [referrer, setReferrer] = useState<User>();

  useEffect(() => {
    if (!referrerId) return;
    const fetchReferrer = async () => {
      try {
        const { data } = await axios.get<User>(`/api/user/${referrerId}`);
        setReferrer(data);
      } catch {
        setReferrer(undefined);
      }
    };
    fetchReferrer();
  }, [referrerId]);

  if (!referrerId || !referrer) {
    return null;
  }

  return <UserDetailsCard user={referrer} title="邀请人" />;
};
