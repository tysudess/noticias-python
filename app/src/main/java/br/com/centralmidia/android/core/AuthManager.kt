package br.com.centralmidia.android.core

import android.content.Context

class AuthManager private constructor(
    private val appContext: Context,
) {
    private val secureStore =
        SecureStore(
            appContext,
        )

    private val client =
        AuthClient(
            appContext,
        )

    @Volatile
    var session: AuthSession? = null
        private set

    fun savedToken(): String? =
        secureStore.loadToken()

    fun validateSaved(): AuthSession? {
        val token =
            savedToken()
                ?: return null

        return try {
            client.validate(
                token,
            ).also {
                session = it
            }
        } catch (
            error: AuthException
        ) {
            /*
             * Não apagar um token válido por falha temporária do servidor
             * (ex.: ScriptLock ocupado no Google Apps Script).
             *
             * Só removemos a sessão local quando o próprio servidor informa
             * que ela realmente não pode mais ser usada.
             */
            if (
                shouldClearSavedToken(
                    error.code,
                )
            ) {
                session = null
                secureStore.clear()
                null
            } else {
                throw error
            }
        }
    }

    fun login(
        username: String,
        password: String,
        remember: Boolean,
    ): AuthSession {
        val s =
            client.login(
                username,
                password,
            )

        session = s

        if (remember) {
            secureStore.saveToken(
                s.token,
            )
        } else {
            secureStore.clear()
        }

        return s
    }

    fun changePassword(
        current: String,
        next: String,
    ): AuthSession {
        val token =
            session?.token
                ?: savedToken()
                ?: throw AuthException(
                    "SESSION_MISSING",
                    "Sessão ausente.",
                )

        val s =
            client.changePassword(
                token,
                current,
                next,
            )

        session = s

        secureStore.saveToken(
            s.token,
        )

        return s
    }

    fun logout() {
        val token =
            session?.token
                ?: savedToken()

        if (
            !token.isNullOrBlank()
        ) {
            client.logout(
                token,
            )
        }

        session = null
        secureStore.clear()
    }

    fun client(): AuthClient =
        client

    private fun shouldClearSavedToken(
        code: String,
    ): Boolean =
        code.uppercase() in
            setOf(
                "SESSION_INVALID",
                "SESSION_REVOKED",
                "SESSION_EXPIRED",
                "USER_NOT_FOUND",
                "USER_BLOCKED",
                "USER_EXPIRED",
                "DEVICE_BLOCKED",
            )

    companion object {
        @Volatile
        private var instance: AuthManager? = null

        fun get(
            context: Context,
        ): AuthManager =
            instance
                ?: synchronized(
                    this,
                ) {
                    instance
                        ?: AuthManager(
                            context.applicationContext,
                        ).also {
                            instance = it
                        }
                }
    }
}
