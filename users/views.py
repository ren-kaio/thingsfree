from django.contrib.auth import get_user_model
from phone_verify.serializers import PhoneSerializer, SMSVerificationSerializer
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.views import \
    TokenObtainPairView as BaseTokenObtainPairView

from . import responses, utils
from .serializers import CreateUserSerializer, TokenObtainPairSerializer

User = get_user_model()


class PhoneVerificationViewSet(GenericViewSet):

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny],
        serializer_class=PhoneSerializer)
    def register(self, request):
        serializer = PhoneSerializer(data=request.data)
        if not serializer.is_valid():
            return responses.INVALID_PHONE_NUMBER

        phone_number = str(serializer.validated_data['phone_number'])
        if User.phone_is_used(phone_number):
            return responses.USED_PHONE_NUMBER

        try:
            session_token = utils.send_security_code(phone_number)
            return responses.create_response(
                200000,
                {'session_token': session_token}
            )
        except Exception:
            return responses.SMS_SENDING_ERROR

    @action(detail=False, methods=["POST"], permission_classes=[AllowAny],
        serializer_class=SMSVerificationSerializer,)
    def verify(self, request):
        serializer = SMSVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return responses.INVALID_SECURITY_CODE
        return responses.VALID_SECURITY_CODE

    @action(detail=False, methods=['POST'], permission_classes=[AllowAny],
            serializer_class=CreateUserSerializer)
    def signup(self, request):
        serializer = SMSVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return responses.INVALID_SECURITY_CODE

        serializer = CreateUserSerializer(data=request.data)
        if not serializer.is_valid():
            errors = ' '.join([
                ' '.join(msg) for msg in serializer.errors.values()
            ])
            return responses.invalid_registration_data(errors)

        try:
            serializer.save()
        except Exception:
            return responses.USER_CREATION_ERROR
        return responses.USER_CREATION_OK


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = TokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except User.DoesNotExist:
            return responses.USER_NOT_FOUND
        except AuthenticationFailed:
            return responses.WRONG_PASSWORD
        except PermissionDenied:
            return responses.USER_IS_BLOCKED
        except Exception as err:
            print('Look: ', err)
            return responses.TOKEN_GENERATION_ERROR

        return responses.create_response(200000, serializer.validated_data)
