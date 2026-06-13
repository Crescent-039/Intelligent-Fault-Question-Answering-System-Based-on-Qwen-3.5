<script>
import { DEFAULT_USER_ID, warmFileCache } from './pages/upload/backend'

export default {
  onLaunch: function () {
    console.log('App Launch')
    warmFileCache(DEFAULT_USER_ID).catch(() => {})
  },
  onShow: function () {
    console.log('App Show')
  },
  onHide: function () {
    console.log('App Hide')
  },
}
</script>

<style>
/*每个页面公共css */
</style>
