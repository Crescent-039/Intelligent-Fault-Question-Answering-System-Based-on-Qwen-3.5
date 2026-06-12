<template>
  <view class="redirect-page"></view>
</template>

<script>
export default {
  onLoad() {
    uni.redirectTo({
      url: '/pages/chat/index',
    })
  },
}
</script>

<style>
.redirect-page {
  min-height: 100vh;
  background: #040914;
}
</style>
