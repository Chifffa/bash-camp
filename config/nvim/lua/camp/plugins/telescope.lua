-- Telescope: fuzzy finding of files, buffers, text and history.
return {
  "nvim-telescope/telescope.nvim",
  dependencies = {
    "nvim-lua/plenary.nvim",
    -- The fast sorter; its build needs make and a C compiler.
    { "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
    "nvim-tree/nvim-web-devicons",
  },
  config = function()
    local telescope = require("telescope")
    local actions = require("telescope.actions")

    telescope.setup({
      defaults = {
        path_display = { "smart" },
        mappings = {
          i = {
            ["<C-k>"] = actions.move_selection_previous,
            ["<C-j>"] = actions.move_selection_next,
            ["<C-q>"] = actions.send_selected_to_qflist + actions.open_qflist,
          },
        },
      },
    })
    -- Where it could not be built, Telescope's own sorter does.
    pcall(telescope.load_extension, "fzf")

    local map = vim.keymap.set
    map("n", "<leader>ff", "<cmd>Telescope find_files<CR>", { desc = "Find Files" })
    map("n", "<leader>fr", "<cmd>Telescope oldfiles<CR>", { desc = "Find Recent Files" })
    map(
      "n",
      "<leader>fb",
      "<cmd>Telescope buffers sort_mru=true sort_lastused=true<CR>",
      { desc = "Find Buffers" }
    )
    map("n", "<leader>sg", "<cmd>Telescope live_grep<CR>", { desc = "Grep" })
    map("n", "<leader>sw", "<cmd>Telescope grep_string<CR>", { desc = "Word" })
    map("n", "<leader>st", "<cmd>TodoTelescope<CR>", { desc = "TODO" })
    map("n", "<leader>:", "<cmd>Telescope command_history<CR>", { desc = "Command History" })
  end,
}
