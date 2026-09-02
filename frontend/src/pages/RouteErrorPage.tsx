import { copy } from '@/locales/zh-CN';
import { isPreloadRouteError } from '@/utils/preloadRecovery';
import { reloadSilently } from '@/utils/silentReload';
import { Button, Result } from 'antd';
import { useRouteError } from 'react-router-dom';

export const RouteErrorPage: React.FC = () => {
  const error = useRouteError();
  const preloadFailure = isPreloadRouteError(error, window.sessionStorage);

  return (
    <Result
      status="error"
      title={
        preloadFailure
          ? copy.routeError.preloadTitle
          : copy.routeError.genericTitle
      }
      subTitle={
        preloadFailure
          ? copy.routeError.preloadDescription
          : copy.routeError.genericDescription
      }
      extra={
        <Button type="primary" onClick={reloadSilently}>
          {copy.routeError.reload}
        </Button>
      }
    />
  );
};
