-- lazy.nvim: installs the specs in camp/plugins at the commits lazy-lock.json pins. `:Lazy update`
-- rewrites the lock in the installed copy, $CAMP_HOME/src; copy it into the checkout to keep it.

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.uv.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "--branch=stable",
    "https://github.com/folke/lazy.nvim.git",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  spec = {
    { import = "camp.plugins" },
    { import = "camp.plugins.lsp" },
  },
  defaults = { lazy = false },
  checker = { enabled = true, notify = false },
  change_detection = { notify = false },
  -- No plugin here needs luarocks.
  rocks = { enabled = false },
  -- The colorscheme while the first start installs everything else.
  install = { colorscheme = { "catppuccin" } },
  performance = {
    rtp = {
      disabled_plugins = { "gzip", "tarPlugin", "tohtml", "tutor", "zipPlugin" },
    },
  },
})
