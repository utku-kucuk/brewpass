import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from './components/layout/AppShell'
import { RequireAuth, RequireProfile } from './components/layout/RouteGuards'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OrderBuilderPage } from './pages/orders/OrderBuilderPage'
import { OrderPage } from './pages/orders/OrderPage'
import { OrdersPage } from './pages/orders/OrdersPage'
import { CheckoutPage } from './pages/pass/CheckoutPage'
import { PassPage } from './pages/pass/PassPage'
import { PaymentsPage } from './pages/pass/PaymentsPage'
import { ProfilePage } from './pages/ProfilePage'
import { ShopDetailPage } from './pages/shops/ShopDetailPage'
import { ShopsPage } from './pages/shops/ShopsPage'
import { SignInPage } from './pages/SignInPage'
import { WelcomePage } from './pages/WelcomePage'

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { path: '/sign-in', element: <SignInPage /> },
      {
        element: <RequireAuth />,
        children: [
          { path: '/welcome', element: <WelcomePage /> },
          {
            element: <RequireProfile />,
            children: [
              { path: '/', element: <HomePage /> },
              { path: '/profile', element: <ProfilePage /> },
              { path: '/shops', element: <ShopsPage /> },
              { path: '/shops/:shopId', element: <ShopDetailPage /> },
              { path: '/pass', element: <PassPage /> },
              { path: '/pass/checkout', element: <CheckoutPage /> },
              { path: '/payments', element: <PaymentsPage /> },
              { path: '/shops/:shopId/order/:productId', element: <OrderBuilderPage /> },
              { path: '/orders', element: <OrdersPage /> },
              { path: '/orders/:orderId', element: <OrderPage /> },
            ],
          },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const createRouter = () => createBrowserRouter(routes)
