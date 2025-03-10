from aws_cdk import core, aws_lambda as lambda_, aws_apigateway as apigw, aws_s3 as s3, aws_dynamodb as dynamodb, aws_sns as sns, aws_s3_notifications as s3n

class TwoTierClassificationStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        bucket = s3.Bucket(self, "ImageUploadBucket")

        table = dynamodb.Table(
            self, "ClassificationResultsTable",
            partition_key=dynamodb.Attribute(name="image_id", type=dynamodb.AttributeType.STRING)
        )

        topic = sns.Topic(self, "ReviewTopic")

        image_processing_lambda = lambda_.Function(
            self, "ImageProcessingLambda",
            runtime=lambda_.Runtime.PYTHON_3_8,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda/image_processor"),
            environment={"TABLE_NAME": table.table_name, "BUCKET_NAME": bucket.bucket_name}
        )

        api_handler_lambda = lambda_.Function(
            self, "ApiHandlerLambda",
            runtime=lambda_.Runtime.PYTHON_3_8,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("lambda/api_handler"),
            environment={"TABLE_NAME": table.table_name}
        )

        api = apigw.LambdaRestApi(
            self, "ImageClassificationApi",
            handler=api_handler_lambda,
            proxy=False
        )
        classify_resource = api.root.add_resource("classify")
        classify_resource.add_method("POST")

        results_resource = api.root.add_resource("results").add_resource("{image_id}")
        results_resource.add_method("GET")

        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(image_processing_lambda)
        )

        table.grant_read_write_data(image_processing_lambda)
        table.grant_read_data(api_handler_lambda)
        bucket.grant_read(image_processing_lambda)
