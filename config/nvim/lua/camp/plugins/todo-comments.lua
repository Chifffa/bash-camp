-- todo-comments: highlights TODO, FIXME and the like, and jumps between them.
return {
  "folke/todo-comments.nvim",
  event = { "BufReadPre", "BufNewFile" },
  dependencies = { "nvim-lua/plenary.nvim" },
  config = function()
    local todo_comments = require("todo-comments")
    todo_comments.setup()
    vim.keymap.set("n", "mlt", todo_comments.jump_next, { desc = "Go to Next TODO Comment" })
    vim.keymap.set("n", "mht", todo_comments.jump_prev, { desc = "Go to Prev TODO Comment" })
  end,
}
