-- which-key: shows the keys that can follow a prefix, and names the groups.
return {
  "folke/which-key.nvim",
  event = "VeryLazy",
  init = function()
    vim.o.timeout = true
    vim.o.timeoutlen = 500
  end,
  opts = {
    plugins = { spelling = true },
  },
  config = function(_, opts)
    local wk = require("which-key")
    wk.setup(opts)
    wk.add({
      { "<leader>f", group = "file/find", icon = "󰈞" },
      { "<leader>w", group = "windows" },
      { "<leader><tab>", group = "tabs" },
      { "<leader>c", group = "code" },
      { "<leader>s", group = "search" },
      { "<leader>d", group = "diagnostics" },
      { "<leader>q", group = "quit/session" },
      { "<leader>r", group = "rename", icon = "󰙩" },
      { "<leader>g", group = "git" },
      { "m", group = "move", icon = "󰆾" },
    })
  end,
}
