-- Trouble: diagnostics and TODOs as a list.
return {
  "folke/trouble.nvim",
  dependencies = { "nvim-tree/nvim-web-devicons", "folke/todo-comments.nvim" },
  cmd = "Trouble",
  keys = {
    {
      "<leader>dw",
      "<cmd>Trouble diagnostics toggle<CR>",
      desc = "Open Trouble Workspace Diagnostics",
    },
    { "<leader>dt", "<cmd>Trouble todo toggle<CR>", desc = "Open TODOs in Trouble" },
  },
  opts = { focus = true },
}
