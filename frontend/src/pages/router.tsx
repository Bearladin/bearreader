/* eslint-disable react-refresh/only-export-components -- Route config exports route arrays, not components */
import { LoadingState } from '@/components/Loading/LoadingState';
import { AuthLayout, MainLayout, ReaderLayout } from '@/components/Layout';
import { lazy, Suspense } from 'react';
import { Navigate, type RouteObject } from 'react-router-dom';

const ChangelogPage = lazy(() =>
  import('./Changelog').then((m) => ({ default: m.ChangelogPage }))
);
const FeedbackDetailsPage = lazy(() =>
  import('./FeedbackDetails').then((m) => ({ default: m.FeedbackDetailsPage }))
);
const FeedbackListPage = lazy(() =>
  import('./FeedbackList').then((m) => ({ default: m.FeedbackListPage }))
);
const ForgotPasswordPage = lazy(() =>
  import('./ForgotPassword').then((m) => ({ default: m.ForgotPasswordPage }))
);
const JobDetailsPage = lazy(() =>
  import('./JobDetails').then((m) => ({ default: m.JobDetailsPage }))
);
const LibraryDetailsPage = lazy(() =>
  import('./LibraryDetails').then((m) => ({ default: m.LibraryDetailsPage }))
);
const LibraryListPage = lazy(() =>
  import('./LibraryList').then((m) => ({ default: m.LibraryListPage }))
);
const LoginPage = lazy(() =>
  import('./Login').then((m) => ({ default: m.LoginPage }))
);
const MainPage = lazy(() =>
  import('./HomePage').then((m) => ({ default: m.HomePage }))
);
const NovelDetailsPage = lazy(() =>
  import('./NovelDetails').then((m) => ({ default: m.NovelDetailsPage }))
);
const NovelListPage = lazy(() =>
  import('./NovelList').then((m) => ({ default: m.NovelListPage }))
);
const NovelReaderPage = lazy(() =>
  import('./NovelReader').then((m) => ({ default: m.NovelReaderPage }))
);
const ResetPasswordPage = lazy(() =>
  import('./ResetPassword').then((m) => ({ default: m.ResetPasswordPage }))
);
const SettingsPage = lazy(() =>
  import('./SettingsPage').then((m) => ({ default: m.SettingsPage }))
);
const SupportedSourcesPage = lazy(() =>
  import('./SupportedSources').then((m) => ({
    default: m.SupportedSourcesPage,
  }))
);
const TrackedNovelsPage = lazy(() =>
  import('./TrackedNovels').then((m) => ({ default: m.TrackedNovelsPage }))
);
const TutorialPage = lazy(() =>
  import('./Tutorial').then((m) => ({ default: m.TutorialPage }))
);
const UserDetailsPage = lazy(() =>
  import('./UserDetails').then((m) => ({ default: m.UserDetailsPage }))
);
const UserListPage = lazy(() =>
  import('./UserList').then((m) => ({ default: m.UserListPage }))
);
const UserProfilePage = lazy(() =>
  import('./UserProfile').then((m) => ({ default: m.UserProfilePage }))
);

const withSuspense = (node: React.ReactNode) => (
  <Suspense fallback={<LoadingState />}>{node}</Suspense>
);

export const AUTH_ROUTES: RouteObject[] = [
  {
    path: '/',
    element: <AuthLayout />,
    children: [
      {
        path: '',
        element: <Navigate to="/login" replace />,
      },
      {
        path: '/login',
        element: withSuspense(<LoginPage />),
      },
      {
        path: '/forgot-password',
        element: withSuspense(<ForgotPasswordPage />),
      },
      {
        path: '/reset-password',
        element: withSuspense(<ResetPasswordPage />),
      },
    ],
  },
];

export const USER_ROUTES: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        path: '',
        element: withSuspense(<MainPage />),
      },
      {
        path: 'profile',
        element: withSuspense(<UserProfilePage />),
      },
      {
        path: 'job/:id',
        element: withSuspense(<JobDetailsPage />),
      },
      {
        path: 'novels',
        element: withSuspense(<NovelListPage />),
      },
      {
        path: 'libraries',
        element: withSuspense(<LibraryListPage />),
      },
      {
        path: 'library/:id',
        element: withSuspense(<LibraryDetailsPage />),
      },
      {
        path: 'novel/:id',
        element: withSuspense(<NovelDetailsPage />),
      },
      {
        path: 'tracked-novels',
        element: withSuspense(<TrackedNovelsPage />),
      },
      {
        path: 'feedbacks',
        element: withSuspense(<FeedbackListPage />),
      },
      {
        path: 'feedback/:id',
        element: withSuspense(<FeedbackDetailsPage />),
      },
      {
        path: 'meta',
        children: [
          {
            path: 'sources',
            element: withSuspense(<SupportedSourcesPage />),
          },
        ],
      },
      {
        path: 'settings',
        element: withSuspense(<SettingsPage />),
      },
      {
        path: 'tutorial',
        element: withSuspense(<TutorialPage />),
      },
      {
        path: 'changelog',
        element: withSuspense(<ChangelogPage />),
      },
    ],
  },
  {
    path: 'read',
    element: <ReaderLayout />,
    children: [
      {
        path: ':id',
        element: withSuspense(<NovelReaderPage />),
      },
    ],
  },
];

export const ADMIN_ROUTES: RouteObject[] = [
  ...USER_ROUTES,
  {
    path: '/admin',
    element: <MainLayout />,
    children: [
      {
        path: 'users',
        element: withSuspense(<UserListPage />),
      },
      {
        path: 'user/:id',
        element: withSuspense(<UserDetailsPage />),
      },
    ],
  },
];
