import { createRouter, createWebHashHistory } from 'vue-router'
import Layout from '@/layout'

const constantRoutes = [
  {
    path: '/redirect',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '/redirect/:path(.*)',
        component: () => import('@/views/redirect/index')
      }
    ]
  },
  {
    path: '/login',
    name: 'Login',
    hidden: true,
    component: () => import('@/views/login/index'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        component: () => import('@/views/dashboard/index'),
        name: 'Dashboard',
        meta: { title: '主页', icon: 'home', affix: true }
      }
    ]
  },
  {
    path: '/user',
    component: Layout,
    name: 'UserPage',
    meta: {
      title: '用户管理',
      icon: 'users'
    },
    children: [
      {
        path: 'user/list',
        component: () => import('@/views/user/user/list'),
        name: 'UserPageList',
        meta: { title: '用户列表', noCache: true }
      },
      {
        path: 'user/edit',
        component: () => import('@/views/user/user/edit'),
        name: 'UserEdit',
        meta: {
          title: '用户编辑',
          noCache: true,
          activeMenu: '/user/user/list'
        },
        hidden: true
      },
      {
        path: 'user/details',
        component: () => import('@/views/user/user/details'),
        name: 'UserDetails',
        meta: {
          title: '用户详情',
          noCache: true,
          activeMenu: '/user/user/list'
        },
        hidden: true
      },
      {
        path: 'admin/list',
        component: () => import('@/views/user/admin/list'),
        name: 'UserAdminPageList',
        meta: { title: '管理员列表', noCache: true }
      },
      {
        path: 'admin/edit',
        component: () => import('@/views/user/admin/edit'),
        name: 'UserAdminEdit',
        meta: {
          title: '管理员编辑',
          noCache: true,
          activeMenu: '/user/admin/list'
        },
        hidden: true
      }
    ]
  },
  {
    path: '/analysis',
    component: Layout,
    name: 'Analysis',
    meta: {
      title: '数据探索分析',
      icon: 'task'
    },
    alwaysShow: true,
    children: [
      {
        path: 'eda',
        component: () => import('@/views/analysis/edaAnalysis'),
        name: 'EdaAnalysisPage',
        meta: { title: '特征探索分析（Python EDA）', noCache: true }
      }
    ]
  },
  {
    path: '/data',
    component: Layout,
    name: 'DataPage',
    meta: {
      title: '数据管理',
      icon: 'table'
    },
    children: [
      {
        path: 'index',
        component: () => import('@/views/data/index'),
        name: 'DataManage',
        meta: { title: '数据管理', noCache: true }
      }
    ]
  },
  {
    path: '/predict',
    component: Layout,
    name: 'PredictPage',
    meta: {
      title: '热度预测',
      icon: 'chart'
    },
    alwaysShow: true,
    children: [
      {
        path: 'index',
        component: () => import('@/views/predict/index'),
        name: 'PredictIndex',
        meta: { title: '热度预测', noCache: true }
      }
    ]
  },
  {
    path: '/attribution',
    component: Layout,
    name: 'AttributionPage',
    meta: {
      title: '归因分析',
      icon: 'eye'
    },
    alwaysShow: true,
    children: [
      {
        path: 'index',
        component: () => import('@/views/attribution/index'),
        name: 'AttributionIndex',
        meta: { title: '归因分析（SHAP）', noCache: true }
      }
    ]
  },
  {
    path: '/grading',
    component: Layout,
    name: 'GradingPage',
    meta: {
      title: '热度分级',
      icon: 'star'
    },
    alwaysShow: true,
    children: [
      {
        path: 'index',
        component: () => import('@/views/grading/index'),
        name: 'GradingIndex',
        meta: { title: '热度分级', noCache: true }
      }
    ]
  },
  {
    path: '/message',
    component: Layout,
    name: 'MessagePage',
    meta: {
      title: '消息中心',
      icon: 'message'
    },
    alwaysShow: true,
    children: [
      {
        path: 'list',
        component: () => import('@/views/message/list'),
        name: 'MessageListPage',
        meta: { title: '消息列表', noCache: true }
      },
      {
        path: 'send',
        component: () => import('@/views/message/send'),
        name: 'MessageSendPage',
        meta: { title: '消息发送', noCache: true }
      }
    ]
  },
  {
    path: '/log',
    component: Layout,
    name: 'LogPage',
    meta: {
      title: '日志中心',
      icon: 'log'
    },
    alwaysShow: true,
    children: [
      {
        path: 'user/list',
        component: () => import('@/views/log/list'),
        name: 'LogUserPage',
        meta: { title: '用户日志', noCache: true }
      }
    ]
  },
  {
    path: '/profile',
    component: Layout,
    hidden: true,
    children: [
      {
        path: 'index',
        component: () => import('@/views/profile/index'),
        name: 'Profile',
        meta: { title: '个人简介', icon: 'user', noCache: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    hidden: true,
    component: () => import('@/views/error-page/404'),
    meta: { title: '404', noCache: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes: constantRoutes
})

export { constantRoutes, router }
