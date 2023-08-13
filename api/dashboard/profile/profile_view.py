from rest_framework.views import APIView

from db.task import KarmaActivityLog, Level
from db.user import User, UserSettings, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import WebHookActions, WebHookCategory
from utils.utils import DiscordWebhooks
from . import profile_serializer


class UserProfileEditView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message='User Not Exists').get_failure_response()
        serializer = profile_serializer.UserProfileEditSerializer(user, many=False)
        return CustomResponse(response=serializer.data).get_success_response()

    def patch(self, request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
            user = User.objects.get(id=user_id)
            serializer = profile_serializer.UserProfileEditSerializer(
                user, data=request.data, partial=True
            )

            if serializer.is_valid():
                serializer.save()

                DiscordWebhooks.general_updates(
                    WebHookCategory.USER_NAME.value,
                    WebHookActions.UPDATE.value,
                    user_id,
                )

                return CustomResponse(response=serializer.data).get_success_response()

            return CustomResponse(response=serializer.errors).get_failure_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class UserProfileAPI(APIView):
    def get(self, request, muid=None):
        if muid is not None:
            user = User.objects.filter(mu_id=muid).first()
            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(user_id=user).first()
            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()
            user_id = user.id
            roles = [role.role.title for role in UserRoleLink.objects.filter(user=user)]
        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)
            roles = JWTUtils.fetch_role(request)

        user = (
            User.objects.select_related("total_karma_user")
            .prefetch_related(
                "user_organization_link_user_id__org",
                "user_organization_link_user_id__department",
                "user_role_link_user__role",
                "userlvllink_set__level",
            )
            .filter(id=user_id)
            .first()
        )

        serializer = profile_serializer.UserProfileSerializer(
            user, many=False, context={"roles": roles}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class UserLogAPI(APIView):
    def get(self, request, muid=None):
        if muid is not None:
            user = User.objects.filter(mu_id=muid).first()
            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(user_id=user).first()
            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()
            user_id = user.id
        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)
        karma_activity_log = KarmaActivityLog.objects.filter(
            user=user_id, appraiser_approved=True
        ).order_by("-created_at")

        if karma_activity_log is None:
            return CustomResponse(
                general_message="No karma details available for user"
            ).get_success_response()

        serializer = profile_serializer.UserLogSerializer(
            karma_activity_log, many=True
        ).data

        return CustomResponse(response=serializer).get_success_response()


class ShareUserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_settings = UserSettings.objects.filter(user_id=user_id).first()
        if user_settings is None:
            return CustomResponse(
                general_message="No data available "
            ).get_failure_response()

        serializer = profile_serializer.ShareUserProfileUpdateSerializer(
            user_settings, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            general_message = (
                "Unleash your vibe, share your profile!"
                if user_settings.is_public
                else "Embrace privacy, safeguard your profile."
            )
            return CustomResponse(
                general_message=general_message
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class UserLevelsAPI(APIView):
    def get(self, request, muid=None):
        if muid is not None:
            user = User.objects.filter(mu_id=muid).first()
            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()
            user_settings = UserSettings.objects.filter(user_id=user).first()
            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()
            user_id = user.id
        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)
        user_levels_link_query = Level.objects.all().order_by("level_order")
        serializer = profile_serializer.UserLevelSerializer(
            user_levels_link_query, many=True, context={"user_id": user_id}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class UserRankAPI(APIView):
    def get(self, request, muid):
        user = User.objects.filter(mu_id=muid).first()
        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()
        roles = [role.role.title for role in UserRoleLink.objects.filter(user=user)]
        serializer = profile_serializer.UserRankSerializer(
            user, many=False, context={"roles": roles}
        )
        return CustomResponse(response=serializer.data).get_success_response()