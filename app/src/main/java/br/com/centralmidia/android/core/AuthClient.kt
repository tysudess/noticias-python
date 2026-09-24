package br.com.centralmidia.android.core

import android.content.Context
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AuthException(
    val code: String,
    override val message: String,
) : Exception(message)

class AuthClient(
    private val context: Context,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    private val jsonType =
        "application/json; charset=utf-8".toMediaType()

    /*
     * O Apps Script compartilhado com Windows/Ubuntu usa ScriptLock.
     * Em momentos de concorrência o servidor pode responder:
     *
     * "Tempo limite do bloqueio: outro processo manteve o bloqueio por muito tempo."
     *
     * O Android não deve tratar isso como senha errada nem exigir novo login
     * imediatamente. Fazemos uma pequena repetição automática e, se ainda
     * estiver ocupado, retornamos uma mensagem amigável.
     */
    @Synchronized
    private fun post(
        payload: JSONObject,
    ): JSONObject {
        var attempt = 0

        while (true) {
            val data = executePost(payload)

            if (data.optBoolean("ok")) {
                return data
            }

            val code =
                data.optString(
                    "code",
                    "AUTH_DENIED",
                )

            val message =
                data.optString(
                    "message",
                    "Acesso não autorizado.",
                )

            if (isServerLockBusy(code, message)) {
                if (
                    attempt <
                    LOCK_RETRY_DELAYS_MS.size
                ) {
                    val delay =
                        LOCK_RETRY_DELAYS_MS[
                            attempt
                        ]

                    attempt++

                    try {
                        Thread.sleep(delay)
                    } catch (
                        interrupted: InterruptedException
                    ) {
                        Thread.currentThread()
                            .interrupt()

                        throw AuthException(
                            "SERVER_BUSY",
                            (
                                "O servidor de autenticação está ocupado. " +
                                    "Tente novamente em alguns segundos."
                                ),
                        )
                    }

                    continue
                }

                throw AuthException(
                    "SERVER_BUSY",
                    (
                        "O servidor de autenticação está ocupado por outra validação. " +
                            "Aguarde alguns segundos e tente novamente."
                        ),
                )
            }

            throw AuthException(
                code,
                message,
            )
        }
    }

    private fun executePost(
        payload: JSONObject,
    ): JSONObject {
        val request = Request.Builder()
            .url(
                SyncedConfig.authUrl(
                    context,
                ),
            )
            .header(
                "Accept",
                "application/json",
            )
            .header(
                "User-Agent",
                "CentralAndroid/1.0",
            )
            .post(
                payload.toString()
                    .toRequestBody(
                        jsonType,
                    ),
            )
            .build()

        client.newCall(request)
            .execute()
            .use { response ->
                if (!response.isSuccessful) {
                    throw AuthException(
                        "HTTP_${response.code}",
                        "Falha HTTP ${response.code}.",
                    )
                }

                val raw =
                    response.body
                        ?.string()
                        .orEmpty()

                if (raw.isBlank()) {
                    throw AuthException(
                        "INVALID_RESPONSE",
                        "O servidor de autenticação retornou uma resposta vazia.",
                    )
                }

                return try {
                    JSONObject(raw)
                } catch (
                    error: Exception
                ) {
                    throw AuthException(
                        "INVALID_RESPONSE",
                        "O servidor de autenticação retornou uma resposta inválida.",
                    )
                }
            }
    }

    private fun isServerLockBusy(
        code: String,
        message: String,
    ): Boolean {
        if (
            !code.equals(
                "SERVER_ERROR",
                ignoreCase = true,
            ) &&
            !code.equals(
                "SERVER_BUSY",
                ignoreCase = true,
            )
        ) {
            return false
        }

        val normalized =
            message.lowercase()

        return (
            "bloqueio" in normalized ||
                "outro processo" in normalized ||
                "lock" in normalized
            )
    }

    fun testServer(): String {
        val request = Request.Builder()
            .url(
                SyncedConfig.authUrl(
                    context,
                ),
            )
            .get()
            .build()

        client.newCall(request)
            .execute()
            .use { response ->
                if (!response.isSuccessful) {
                    throw AuthException(
                        "HTTP_${response.code}",
                        "Servidor indisponível.",
                    )
                }

                val root =
                    JSONObject(
                        response.body
                            ?.string()
                            .orEmpty(),
                    )

                if (
                    !root.optBoolean(
                        "ok",
                    )
                ) {
                    throw AuthException(
                        "SERVER",
                        "Servidor não confirmou status online.",
                    )
                }

                return root.optString(
                    "version",
                    "desconhecida",
                )
            }
    }

    fun login(
        username: String,
        password: String,
    ): AuthSession =
        sessionFrom(
            post(
                JSONObject().apply {
                    put(
                        "action",
                        "login",
                    )
                    put(
                        "username",
                        username,
                    )
                    put(
                        "password",
                        password,
                    )
                    put(
                        "device_id",
                        DeviceIdentity.id(
                            context,
                        ),
                    )
                    put(
                        "device_name",
                        DeviceIdentity.name(),
                    )
                    put(
                        "os",
                        DeviceIdentity.os(),
                    )
                },
            ),
        )

    fun validate(
        token: String,
    ): AuthSession =
        sessionFrom(
            post(
                JSONObject().apply {
                    put(
                        "action",
                        "validate",
                    )
                    put(
                        "token",
                        token,
                    )
                    put(
                        "device_id",
                        DeviceIdentity.id(
                            context,
                        ),
                    )
                },
            ),
        )

    fun changePassword(
        token: String,
        current: String,
        next: String,
    ): AuthSession =
        sessionFrom(
            post(
                JSONObject().apply {
                    put(
                        "action",
                        "change_password",
                    )
                    put(
                        "token",
                        token,
                    )
                    put(
                        "device_id",
                        DeviceIdentity.id(
                            context,
                        ),
                    )
                    put(
                        "current_password",
                        current,
                    )
                    put(
                        "new_password",
                        next,
                    )
                },
            ),
        )

    fun logout(
        token: String,
    ) {
        runCatching {
            post(
                JSONObject().apply {
                    put(
                        "action",
                        "logout",
                    )
                    put(
                        "token",
                        token,
                    )
                    put(
                        "device_id",
                        DeviceIdentity.id(
                            context,
                        ),
                    )
                },
            )
        }
    }

    private fun sessionFrom(
        root: JSONObject,
    ): AuthSession {
        val userRoot =
            root.optJSONObject(
                "user",
            )
                ?: JSONObject()

        val permissionsJson =
            userRoot.optJSONArray(
                "permissions",
            )

        val permissions =
            buildSet {
                if (
                    permissionsJson != null
                ) {
                    for (
                        i in 0 until
                            permissionsJson.length()
                    ) {
                        add(
                            permissionsJson
                                .optString(i)
                                .lowercase(),
                        )
                    }
                }
            }

        return AuthSession(
            token =
                root.getString(
                    "token",
                ),
            expiresAt =
                root.optString(
                    "expires_at",
                )
                    .ifBlank {
                        null
                    },
            user =
                AuthUser(
                    username =
                        userRoot.optString(
                            "username",
                        ),
                    name =
                        userRoot.optString(
                            "name",
                        ),
                    profile =
                        userRoot.optString(
                            "profile",
                        ),
                    permissions =
                        permissions,
                    mustChangePassword =
                        userRoot.optBoolean(
                            "must_change_password",
                            false,
                        ),
                ),
        )
    }

    companion object {
        private val LOCK_RETRY_DELAYS_MS =
            longArrayOf(
                900L,
                1_800L,
            )
    }
}
