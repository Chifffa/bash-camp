-- nvim-treesitter-textobjects: select, swap and move by syntax node - assignments, arguments,
-- conditionals, loops, calls, functions, classes and comments.

-- { keys, text object, description }, in visual and operator-pending mode.
local selects = {
  { "a=", "@assignment.outer", "Select Outer Assignment Part" },
  { "i=", "@assignment.inner", "Select Inner Assignment Part" },
  { "l=", "@assignment.lhs", "Select LHS Assignment Part" },
  { "r=", "@assignment.rhs", "Select RHS Assignment Part" },
  { "aa", "@parameter.outer", "Select Outer Argument Part" },
  { "ia", "@parameter.inner", "Select Inner Argument Part" },
  { "ai", "@conditional.outer", "Select Outer Conditional Part" },
  { "ii", "@conditional.inner", "Select Inner Conditional Part" },
  { "al", "@loop.outer", "Select Outer Loop Part" },
  { "il", "@loop.inner", "Select Inner Loop Part" },
  { "ac", "@call.outer", "Select Outer Function Call Part" },
  { "ic", "@call.inner", "Select Inner Function Call Part" },
  { "af", "@function.outer", "Select Outer Function Part" },
  { "if", "@function.inner", "Select Inner Function Part" },
  { "as", "@class.outer", "Select Outer Class Part" },
  { "is", "@class.inner", "Select Inner Class Part" },
  { "a/", "@comment.outer", "Select Outer Comment Part" },
  { "i/", "@comment.inner", "Select Inner Comment Part" },
}

-- { keys, swap function, text object, description }, in normal mode.
local swaps = {
  { "mspl", "swap_next", "@parameter.outer", "Swap Next Parameter with Current" },
  { "msfl", "swap_next", "@function.outer", "Swap Next Function with Current" },
  { "msph", "swap_previous", "@parameter.outer", "Swap Prev Parameter with Current" },
  { "msfh", "swap_previous", "@function.outer", "Swap Prev Function with Current" },
}

-- { keys, move function, text object, description }: m, then l for the next one or h for the
-- previous, the object's letter, and k for its start or j for its end.
local moves = {
  { "mlck", "goto_next_start", "@call.outer", "Go to Next Function Call Start" },
  { "mlfk", "goto_next_start", "@function.outer", "Go to Next Function Def Start" },
  { "mlsk", "goto_next_start", "@class.outer", "Go to Next Struct Start" },
  { "mlik", "goto_next_start", "@conditional.outer", "Go to Next Conditional Start" },
  { "mllk", "goto_next_start", "@loop.outer", "Go to Next Loop Start" },
  { "mlcj", "goto_next_end", "@call.outer", "Go to Next Function Call End" },
  { "mlfj", "goto_next_end", "@function.outer", "Go to Next Function Def End" },
  { "mlsj", "goto_next_end", "@class.outer", "Go to Next Struct End" },
  { "mlij", "goto_next_end", "@conditional.outer", "Go to Next Conditional End" },
  { "mllj", "goto_next_end", "@loop.outer", "Go to Next Loop End" },
  { "mhck", "goto_previous_start", "@call.outer", "Go to Prev Function Call Start" },
  { "mhfk", "goto_previous_start", "@function.outer", "Go to Prev Function Def Start" },
  { "mhsk", "goto_previous_start", "@class.outer", "Go to Prev Struct Start" },
  { "mhik", "goto_previous_start", "@conditional.outer", "Go to Prev Conditional Start" },
  { "mhlk", "goto_previous_start", "@loop.outer", "Go to Prev Loop Start" },
  { "mhcj", "goto_previous_end", "@call.outer", "Go to Prev Function Call End" },
  { "mhfj", "goto_previous_end", "@function.outer", "Go to Prev Function Def End" },
  { "mhsj", "goto_previous_end", "@class.outer", "Go to Prev Struct End" },
  { "mhij", "goto_previous_end", "@conditional.outer", "Go to Prev Conditional End" },
  { "mhlj", "goto_previous_end", "@loop.outer", "Go to Prev Loop End" },
}

return {
  "nvim-treesitter/nvim-treesitter-textobjects",
  branch = "main",
  event = "VeryLazy",
  config = function()
    require("nvim-treesitter-textobjects").setup({ select = { lookahead = true } })

    local select = require("nvim-treesitter-textobjects.select")
    for _, m in ipairs(selects) do
      vim.keymap.set({ "x", "o" }, m[1], function()
        select.select_textobject(m[2], "textobjects")
      end, { desc = m[3] })
    end

    local swap = require("nvim-treesitter-textobjects.swap")
    for _, m in ipairs(swaps) do
      vim.keymap.set("n", m[1], function()
        swap[m[2]](m[3], "textobjects")
      end, { desc = m[4] })
    end

    local move = require("nvim-treesitter-textobjects.move")
    for _, m in ipairs(moves) do
      vim.keymap.set({ "n", "x", "o" }, m[1], function()
        move[m[2]](m[3], "textobjects")
      end, { desc = m[4] })
    end
  end,
}
