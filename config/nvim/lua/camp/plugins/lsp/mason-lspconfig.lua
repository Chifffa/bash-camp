-- mason-lspconfig and mason-tool-installer: what mason installs on the first start - the servers
-- lspconfig.lua needs from it, and the formatters conform runs. Installed servers are also enabled.
return {
  "williamboman/mason-lspconfig.nvim",
  dependencies = {
    "williamboman/mason.nvim",
    "WhoIsSethDaniel/mason-tool-installer.nvim",
  },
  event = { "BufReadPre", "BufNewFile" },
  config = function()
    require("mason-lspconfig").setup({
      ensure_installed = { "lua_ls", "basedpyright" },
    })
    -- ruff and stylua come from bash-camp's toolchain.
    require("mason-tool-installer").setup({
      ensure_installed = { "shfmt", "tombi", "tex-fmt" },
    })
  end,
}
