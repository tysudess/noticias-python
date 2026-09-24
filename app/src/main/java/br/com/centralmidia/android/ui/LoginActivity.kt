package br.com.centralmidia.android.ui

import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import br.com.centralmidia.android.core.dp
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout

class LoginActivity : BaseActivity() {
    private lateinit var status: TextView
    private lateinit var username: TextInputEditText
    private lateinit var password: TextInputEditText
    private lateinit var loginButton: MaterialButton
    private lateinit var progress: ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
        window.statusBarColor = Color.TRANSPARENT
        window.navigationBarColor = Color.TRANSPARENT
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowCompat.getInsetsController(window, window.decorView).apply {
            isAppearanceLightStatusBars = true
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                isAppearanceLightNavigationBars = true
            }
        }

        val shell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                intArrayOf(
                    Color.rgb(242, 248, 255),
                    Color.rgb(248, 246, 255),
                    Color.WHITE,
                ),
            )
        }

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            clipToPadding = false
        }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(24), dp(26), dp(24), dp(28))
        }
        scroll.addView(
            content,
            ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
            ),
        )
        shell.addView(
            scroll,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f,
            ),
        )
        setContentView(shell)

        ViewCompat.setOnApplyWindowInsetsListener(shell) { _, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            shell.setPadding(0, bars.top, 0, bars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(shell)

        content.addView(brandBlock())
        content.addView(loginCard(), marginTop(dp(22)))
        content.addView(
            text(
                "Autenticação integrada ao mesmo servidor da Central Windows/Ubuntu.",
                10.5f,
                Color.rgb(94, 113, 145),
            ).apply { gravity = Gravity.CENTER },
            marginTop(dp(14)),
        )

        val saved = auth.savedToken()
        if (!saved.isNullOrBlank()) {
            setBusy(true)
            statusCard("Validando sessão salva…", false)
            io(
                { auth.validateSaved() },
                { session ->
                    setBusy(false)
                    if (session != null) {
                        if (session.user.mustChangePassword) {
                            PasswordDialogs.show(this, true) { openMain() }
                        } else {
                            openMain()
                        }
                    } else {
                        statusCard("Sessão expirada. Faça login novamente.", true)
                    }
                },
                { error ->
                    setBusy(false)
                    statusCard(
                        error.message
                            ?: "Não foi possível validar a sessão agora. Tente novamente.",
                        true,
                    )
                },
            )
        }
    }

    private fun brandBlock(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER_HORIZONTAL

        addView(
            LinearLayout(this@LoginActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.BOTTOM
                listOf(18, 28, 39).forEachIndexed { index, height ->
                    addView(
                        android.view.View(this@LoginActivity).apply {
                            background = rounded(
                                when (index) {
                                    0 -> Color.rgb(77, 165, 255)
                                    1 -> Color.rgb(45, 130, 242)
                                    else -> Color.rgb(23, 92, 181)
                                },
                                dp(6).toFloat(),
                            )
                        },
                        LinearLayout.LayoutParams(dp(8), dp(height)).apply {
                            marginEnd = dp(5)
                        },
                    )
                }
            },
        )

        addView(
            text(
                "Central Inteligente de Mídia",
                29f,
                Color.rgb(7, 43, 90),
                true,
            ).apply { gravity = Gravity.CENTER },
            marginTop(dp(13)),
        )
        addView(
            text(
                "Acesso seguro • conexão direta • sem proxy",
                13f,
                Color.rgb(89, 111, 145),
            ).apply { gravity = Gravity.CENTER },
            marginTop(dp(5)),
        )
    }

    private fun loginCard(): MaterialCardView {
        val card = MaterialCardView(this).apply {
            radius = dp(26).toFloat()
            cardElevation = dp(8).toFloat()
            strokeWidth = dp(1)
            strokeColor = Color.rgb(218, 228, 242)
            setCardBackgroundColor(Color.WHITE)
            setContentPadding(dp(20), dp(22), dp(20), dp(22))
        }

        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        box.addView(
            text(
                "Bem-vindo",
                22f,
                Color.rgb(7, 43, 90),
                true,
            ),
        )
        box.addView(
            text(
                "Entre com o mesmo usuário e senha utilizados no Windows e Ubuntu.",
                11.5f,
                Color.rgb(94, 113, 145),
            ),
            marginTop(dp(5)),
        )

        val userLayout = inputLayout("Usuário", false)
        username = userLayout.editText as TextInputEditText
        box.addView(userLayout, marginTop(dp(20)))

        val passLayout = inputLayout("Senha", true)
        password = passLayout.editText as TextInputEditText
        box.addView(passLayout, marginTop(dp(12)))

        val remember = CheckBox(this).apply {
            text = "Manter conectado neste aparelho"
            isChecked = true
            textSize = 11.5f
            setTextColor(Color.rgb(34, 57, 91))
            buttonTintList = ColorStateList.valueOf(Color.rgb(20, 126, 246))
        }
        box.addView(remember, marginTop(dp(10)))

        val statusShell = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(10), dp(12), dp(10))
            background = rounded(
                Color.rgb(244, 248, 253),
                dp(12).toFloat(),
                Color.rgb(220, 230, 243),
            )
        }
        progress = ProgressBar(this).apply {
            isIndeterminate = true
            visibility = android.view.View.GONE
        }
        statusShell.addView(
            progress,
            LinearLayout.LayoutParams(dp(22), dp(22)).apply { marginEnd = dp(9) },
        )
        status = text(
            "Informe seu usuário e senha.",
            11.5f,
            Color.rgb(76, 96, 128),
        )
        statusShell.addView(
            status,
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f),
        )
        box.addView(statusShell, marginTop(dp(12)))

        loginButton = MaterialButton(this).apply {
            text = "Entrar na Central"
            isAllCaps = false
            textSize = 15f
            setTypeface(typeface, Typeface.BOLD)
            cornerRadius = dp(17)
            minimumHeight = 0
            insetTop = 0
            insetBottom = 0
            backgroundTintList = ColorStateList.valueOf(Color.rgb(16, 104, 207))
            setTextColor(Color.WHITE)
            setOnClickListener {
                val u = username.text?.toString()?.trim().orEmpty()
                val p = password.text?.toString().orEmpty()
                if (u.isBlank() || p.isBlank()) {
                    statusCard("Preencha usuário e senha para continuar.", true)
                    if (u.isBlank()) userLayout.error = "Informe o usuário" else userLayout.error = null
                    if (p.isBlank()) passLayout.error = "Informe a senha" else passLayout.error = null
                    return@setOnClickListener
                }
                userLayout.error = null
                passLayout.error = null
                setBusy(true)
                statusCard("Validando acesso…", false)
                io(
                    { auth.login(u, p, remember.isChecked) },
                    { session ->
                        setBusy(false)
                        if (session.user.mustChangePassword) {
                            PasswordDialogs.show(this, true, p) { openMain() }
                        } else {
                            openMain()
                        }
                    },
                    {
                        setBusy(false)
                        statusCard(it.message ?: "Falha no login.", true)
                    },
                )
            }
        }
        box.addView(
            loginButton,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)).apply {
                topMargin = dp(16)
            },
        )

        val test = MaterialButton(this).apply {
            text = "Testar conexão com o servidor"
            isAllCaps = false
            textSize = 12f
            cornerRadius = dp(15)
            minimumHeight = 0
            insetTop = 0
            insetBottom = 0
            backgroundTintList = ColorStateList.valueOf(Color.WHITE)
            strokeWidth = dp(1)
            strokeColor = ColorStateList.valueOf(Color.rgb(197, 216, 238))
            setTextColor(Color.rgb(7, 62, 127))
            setOnClickListener {
                statusCard("Testando conexão…", false)
                progress.visibility = android.view.View.VISIBLE
                io(
                    { auth.client().testServer() },
                    {
                        progress.visibility = android.view.View.GONE
                        statusCard("Servidor acessível • versão $it", false)
                    },
                    {
                        progress.visibility = android.view.View.GONE
                        statusCard(it.message ?: "Servidor indisponível.", true)
                    },
                )
            }
        }
        box.addView(
            test,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48)).apply {
                topMargin = dp(9)
            },
        )

        card.addView(box)
        return card
    }

    private fun inputLayout(label: String, passwordField: Boolean): TextInputLayout {
        val layout = TextInputLayout(this).apply {
            hint = label
            boxBackgroundMode = TextInputLayout.BOX_BACKGROUND_OUTLINE
            boxBackgroundColor = Color.WHITE
            boxStrokeColor = Color.rgb(28, 124, 229)
            boxStrokeWidth = dp(1)
            boxStrokeWidthFocused = dp(2)
            setBoxCornerRadii(
                dp(15).toFloat(),
                dp(15).toFloat(),
                dp(15).toFloat(),
                dp(15).toFloat(),
            )
            hintTextColor = ColorStateList.valueOf(Color.rgb(64, 91, 127))
            defaultHintTextColor = ColorStateList.valueOf(Color.rgb(92, 111, 143))
            if (passwordField) {
                endIconMode = TextInputLayout.END_ICON_PASSWORD_TOGGLE
            }
        }
        val edit = TextInputEditText(layout.context).apply {
            textSize = 16f
            setTextColor(Color.rgb(8, 40, 82))
            setHintTextColor(Color.rgb(112, 130, 157))
            setSingleLine(true)
            inputType = if (passwordField) {
                InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            } else {
                InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_NORMAL
            }
            setPadding(dp(13), dp(7), dp(13), dp(7))
        }
        layout.addView(
            edit,
            LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)),
        )
        return layout
    }

    private fun statusCard(message: String, isError: Boolean) {
        status.text = message
        status.setTextColor(
            if (isError) Color.rgb(190, 45, 68) else Color.rgb(58, 82, 117),
        )
        progress.visibility = if (loginButton.isEnabled) android.view.View.GONE else android.view.View.VISIBLE
    }

    private fun setBusy(busy: Boolean) {
        loginButton.isEnabled = !busy
        username.isEnabled = !busy
        password.isEnabled = !busy
        progress.visibility = if (busy) android.view.View.VISIBLE else android.view.View.GONE
        loginButton.alpha = if (busy) 0.72f else 1f
    }

    private fun openMain() {
        startActivity(
            Intent(this, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP),
        )
        finish()
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }

    private fun text(
        value: String,
        size: Float,
        color: Int,
        bold: Boolean = false,
    ) = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
    }

    private fun rounded(
        color: Int,
        radius: Float,
        strokeColor: Int? = null,
    ) = GradientDrawable().apply {
        shape = GradientDrawable.RECTANGLE
        setColor(color)
        cornerRadius = radius
        if (strokeColor != null) setStroke(dp(1), strokeColor)
    }

    private fun marginTop(value: Int) = LinearLayout.LayoutParams(
        ViewGroup.LayoutParams.MATCH_PARENT,
        ViewGroup.LayoutParams.WRAP_CONTENT,
    ).apply { topMargin = value }
}
