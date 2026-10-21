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
        meta: { title: '主页', icon: 'home', group: '项目概览', affix: true }
      }
    ]
  },
  {
    path: '/about',
    component: Layout,
    name: 'AboutPage',
    children: [
      {
        path: 'index',
        component: () => import('@/views/about/index'),
        name: 'AboutIndex',
        meta: { title: '项目介绍', icon: 'guide', group: '项目概览', noCache: true }
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
        meta: { title: '用户列表', icon: 'users', group: '系统管理', noCache: true }
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
        meta: { title: '管理员列表', icon: 'people', group: '系统管理', noCache: true }
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
        meta: { title: '特征探索分析', icon: 'task', group: '数据与特征', noCache: true }
      }
    ]
  },
  {
    path: '/data',
    component: Layout,
    name: 'DataPage',
    meta: {
      title: '',
      icon: 'table'
    },
    children: [
      {
        path: 'index',
        component: () => import('@/views/data/index'),
        name: 'DataManage',
        meta: { title: '数据管理', icon: 'table', group: '数据与特征', noCache: true }
      },
      {
        path: 'comparison',
        component: () => import('@/views/comparison/index'),
        name: 'PlatformComparison',
        meta: { title: '平台对比', icon: 'peoples', group: '数据与特征', noCache: true }
      }
    ]
  },
  {
    path: '/predict',
    component: Layout,
    name: 'PredictPage',
    meta: {
      title: '',
      icon: 'chart'
    },
    children: [
      {
        path: 'index',
        component: () => import('@/views/predict/index'),
        name: 'PredictIndex',
        meta: { title: '热度预测', icon: 'chart', group: '模型与归因', noCache: true }
      }
    ]
  },
  {
    path: '/attribution',
    component: Layout,
    name: 'AttributionPage',
    meta: {
      title: '',
      icon: 'eye'
    },
    children: [
      {
        path: 'index',
        component: () => import('@/views/attribution/index'),
        name: 'AttributionIndex',
        meta: { title: '归因分析', icon: 'eye', group: '模型与归因', noCache: true }
      }
    ]
  },
  {
    path: '/grading',
    component: Layout,
    name: 'GradingPage',
    meta: {
      title: '',
      icon: 'star'
    },
    children: [
      {
        path: 'index',
        component: () => import('@/views/grading/index'),
        name: 'GradingIndex',
        meta: { title: '热度分级', icon: 'star', group: '模型与归因', noCache: true }
      }
    ]
  },
  {
    path: '/evaluation',
    component: Layout,
    name: 'EvaluationPage',
    children: [
      {
        path: 'index',
        component: () => import('@/views/evaluation/index'),
        name: 'EvaluationIndex',
        meta: { title: '模型评估', icon: 'skill', group: '模型与归因', noCache: true }
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
        meta: { title: '个人中心', icon: 'user', noCache: true }
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
